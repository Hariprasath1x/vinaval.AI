import pytest
from app.services.exam_service import ExamService
from app.schemas.exam import ExamSelectionRequest
from app.models.user import User


def test_list_exams():
    service = ExamService()
    exams = service.list_exams()
    assert len(exams) >= 2
    exam_ids = [e.id for e in exams]
    assert "NEET" in exam_ids
    assert "TNPSC" in exam_ids


def test_get_user_exam(mock_user):
    service = ExamService()
    res = service.get_user_exam(mock_user)
    assert res.selected_exam == "NEET"
    assert res.message == "OK"


@pytest.mark.asyncio
async def test_select_exam_valid(db_session, mock_user):
    service = ExamService(db_session)
    res = await service.select_exam(mock_user, "tnpsc")
    assert res.selected_exam == "TNPSC"
    assert "successfully" in res.message


@pytest.mark.asyncio
async def test_select_exam_invalid(db_session, mock_user):
    service = ExamService(db_session)
    with pytest.raises(ValueError, match="Invalid exam 'INVALID'"):
        await service.select_exam(mock_user, "INVALID")


@pytest.mark.asyncio
async def test_exam_api_endpoints(client):
    # Test GET /api/v1/exams
    res = await client.get("/api/v1/exams")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2

    # Test GET /api/v1/exams/me
    res_me = await client.get("/api/v1/exams/me")
    assert res_me.status_code == 200
    assert res_me.json()["selected_exam"] == "NEET"

    # Test POST /api/v1/exams/select
    res_sel = await client.post("/api/v1/exams/select", json={"exam_id": "TNPSC"})
    assert res_sel.status_code == 200
    assert res_sel.json()["selected_exam"] == "TNPSC"
