import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.firebase import verify_firebase_token
from app.core.security import create_access_token, create_refresh_token, decode_access_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate, TokenResponse, UserResponse, SignupRequest, LoginRequest, RefreshTokenRequest


def _hash_password(plain: str) -> str:
    pwd_bytes = plain.encode('utf-8')[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt(rounds=10)).decode('utf-8')


def _verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        pwd_bytes = plain.encode('utf-8')[:72]
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False




class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    # ── Email / Password Sign-Up ──────────────────────────────────────────────

    async def signup(self, req: SignupRequest) -> TokenResponse:
        """Register a new user with email + password."""
        existing = await self.repo.get_by_email(req.email)
        if existing:
            if not existing.hashed_password:
                # User existed without a password (legacy Google account). Set password now.
                existing.hashed_password = _hash_password(req.password)
                if req.name:
                    existing.name = req.name
                await self.db.commit()
                await self.db.refresh(existing)
                access_token = create_access_token(data={"sub": str(existing.id)})
                refresh_token = create_refresh_token(data={"sub": str(existing.id)})
                return TokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    user=UserResponse.model_validate(existing),
                )

            raise ValueError("An account with this email already exists. Please log in.")

        hashed = _hash_password(req.password)
        user = await self.repo.create(
            UserCreate(
                email=req.email,
                name=req.name,
                hashed_password=hashed,
            )
        )
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )

    # ── Email / Password Login ────────────────────────────────────────────────

    async def login(self, req: LoginRequest) -> TokenResponse:
        """Authenticate a user by email and password."""
        user = await self.repo.get_by_email(req.email)

        if not user:
            raise ValueError("No account found with this email. Please sign up first.")

        # Google-only accounts (no password set) → direct to Google Sign-In
        if user.google_id and not user.hashed_password:
            raise ValueError(
                "This account uses Google Sign-In. "
                "Please click 'Continue with Google' to log in."
            )

        if not user.hashed_password:
            raise ValueError(
                "No password set for this account. "
                "Please use 'Forgot Password' to set one, or sign up again."
            )

        if not _verify_password(req.password, user.hashed_password):
            raise ValueError("Incorrect password. Please try again.")

        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )



    # ── Firebase (Google OAuth) ───────────────────────────────────────────────

    async def login_with_firebase(self, id_token: str) -> TokenResponse:
        """Verify a Firebase ID token, upsert the user, return a JWT."""
        user_info = verify_firebase_token(id_token)

        user = await self.repo.get_by_google_id(user_info["uid"])
        if not user:
            # Check if email already exists (e.g., signed up via email/pw)
            user = await self.repo.get_by_email(user_info["email"])
            if user:
                # Link Google ID to existing account
                user.google_id = user_info["uid"]
                await self.db.commit()
                await self.db.refresh(user)
            else:
                try:
                    user = await self.repo.create(
                        UserCreate(
                            google_id=user_info["uid"],
                            email=user_info["email"],
                            name=user_info["name"],
                            avatar_url=user_info.get("picture"),
                        )
                    )
                except IntegrityError:
                    # Fallback in case of a race condition (e.g., React StrictMode firing login twice)
                    await self.db.rollback()
                    user = await self.repo.get_by_email(user_info["email"])
                    if user and not user.google_id:
                        user.google_id = user_info["uid"]
                        await self.db.commit()
                        await self.db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )

    # ── Refresh Token ─────────────────────────────────────────────────────────

    async def refresh_token(self, req: RefreshTokenRequest) -> TokenResponse:
        """Exchange a valid refresh token for a new access token and refresh token."""
        payload = decode_access_token(req.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid or expired refresh token.")
            
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload.")
            
        user = await self.repo.get_by_id(int(user_id))
        if not user:
            raise ValueError("User not found.")
            
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )

    # ── Profile Updates ───────────────────────────────────────────────────────

    async def update_profile(self, user_id: int, name: str) -> UserResponse:
        user = await self.repo.update_name(user_id, name)
        if not user:
            raise ValueError("User not found")
        return UserResponse.model_validate(user)

    async def change_password(self, user_id: int, current_pw: str, new_pw: str) -> bool:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if not user.hashed_password:
            raise ValueError("This account uses Google Sign-In and does not have a password.")
        
        if not _verify_password(current_pw, user.hashed_password):
            raise ValueError("Incorrect current password.")

        hashed = _hash_password(new_pw)
        await self.repo.update_password(user_id, hashed)
        return True
