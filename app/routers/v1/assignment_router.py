from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.services import assignment as assignment_service
from app.core.security import get_current_user
from app.schemas.assignment import AssignmentCreate
from app.schemas.context import UserContext

router = APIRouter()

@router.post("/assignments", status_code=status.HTTP_201_CREATED)
async def create_assignment(
    assignment: AssignmentCreate,
    user: UserContext = Depends(get_current_user),
):
    try:
        new_id = await assignment_service.create_assignment(assignment, user)

        location = f"/api/v1/assignments/{new_id}"

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Assignment created successfully"},
            headers={"Location": str(location)}
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/assignments")
async def list_assignments(user: UserContext = Depends(get_current_user)):
    return await assignment_service.list_assignments(user)


@router.get("/assignments/{assignment_id}")
async def get_assignment(
    assignment_id: str,
    user: UserContext = Depends(get_current_user)
):
    try:
        result = await assignment_service.get_assignment(assignment_id, user)
        if not result:
            raise HTTPException(status_code=404, detail="Assignment not found")
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: str,
    user: UserContext = Depends(get_current_user),
):
    try:
        deleted = await assignment_service.delete_assignment(assignment_id, user)
        if not deleted:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
