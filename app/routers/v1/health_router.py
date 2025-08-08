from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Simple health endpoint to verify the service is running.
    """
    return {"status": "ok"}