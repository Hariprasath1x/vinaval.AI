from sqlalchemy.ext.asyncio import AsyncSession
from app.core.firebase import verify_firebase_token
from app.core.security import create_access_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate, TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def login_with_firebase(self, id_token: str) -> TokenResponse:
        """
        Verify a Firebase ID token, upsert the user in PostgreSQL,
        and return a short-lived JWT for all subsequent API calls.
        """
        # Step 1: Verify Firebase ID token → get user info
        user_info = verify_firebase_token(id_token)

        # Step 2: Upsert user in our DB (create on first login, skip on repeat)
        user = await self.repo.get_by_google_id(user_info["uid"])
        if not user:
            user = await self.repo.create(
                UserCreate(
                    google_id=user_info["uid"],
                    email=user_info["email"],
                    name=user_info["name"],
                    avatar_url=user_info.get("picture"),
                )
            )

        # Step 3: Issue our own JWT — backend is no longer Firebase-dependent
        access_token = create_access_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )
