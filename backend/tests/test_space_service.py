import pytest
from app.services.space_service import SpaceService

@pytest.mark.asyncio
async def test_space_service_init(db_session):
    # Basic skeleton test for space service
    service = SpaceService(db_session)
    assert service is not None
