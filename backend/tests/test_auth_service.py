import pytest
from app.services.auth_service import AuthService
from app.schemas.auth import SignupRequest

@pytest.mark.asyncio
async def test_auth_service_signup(db_session):
    # Basic skeleton test for auth service
    service = AuthService(db_session)
    assert service is not None
