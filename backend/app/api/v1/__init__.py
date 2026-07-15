from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.exam import router as exam_router
from app.api.v1.space import router as space_router
from app.api.v1.quiz import router as quiz_router
from app.api.v1.flashcard import router as flashcard_router
from app.api.v1.document import router as document_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(exam_router)
router.include_router(space_router)
router.include_router(quiz_router)
router.include_router(flashcard_router)
router.include_router(document_router)
