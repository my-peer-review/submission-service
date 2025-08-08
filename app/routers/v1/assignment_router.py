from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.services import assignment as assignment_service
from app.core.security import get_current_user
from app.schemas.assignment import AssignmentCreate
from app.schemas.context import UserContext

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Simple health endpoint to verify service is running.
    """
    return {"status": "ok"}

@router.post("/")
async def create_assignment(
    assignment: AssignmentCreate,
    user: UserContext = Depends(get_current_user)
):
    try:
        return await assignment_service.create_assignment(assignment, user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/")
async def list_assignments(user: UserContext = Depends(get_current_user)):
    return await assignment_service.list_assignments(user)


@router.get("/{assignment_id}")
async def get_assignment(
    assignment_id: UUID,
    user: UserContext = Depends(get_current_user)
):
    try:
        result = await assignment_service.get_assignment(assignment_id, user)
        if not result:
            raise HTTPException(status_code=404, detail="Assignment not found")
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
@router.get("/health")
async def health_check():
    """
    Simple health endpoint to verify service is running.
    """
    return {"status": "ok"}
