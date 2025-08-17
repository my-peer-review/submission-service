from fastapi import APIRouter

router = APIRouter()

@router.get("/submissions/health")
async def health_check():
    return {"status": "ok"}