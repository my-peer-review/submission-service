from uuid import uuid4
from datetime import datetime, timezone
from app.schemas.assignment import AssignmentCreate, Assignment
from app.schemas.context import UserContext
from app.database.assignment_repo import assignment_repo

async def create_assignment(data: AssignmentCreate, user: UserContext) -> str:
    if "teacher" not in user.role:
        raise PermissionError("Only teachers can create assignments")

    new_id = str(uuid4())
    assignment_dict = {
        "_id": new_id,
        "createdAt": datetime.now(timezone.utc),
        "teacherId": user.user_id,
        **data.model_dump()
    }

    await assignment_repo.create(assignment_dict)
    return new_id

async def list_assignments(user: UserContext):
    if "teacher" in user.role:
        docs = await assignment_repo.find_for_teacher(user.user_id)
    elif "student" in user.role:
        docs = await assignment_repo.find_for_student(user.user_id)
    else:
        return []

    return [Assignment(**_from_mongo(doc)) for doc in docs]

async def get_assignment(assignment_id: str, user: UserContext):
    doc = await assignment_repo.find_one(assignment_id)
    if not doc:
        return None

    if user.role == "teacher" and doc["teacherId"] != user.user_id:
        raise PermissionError("Accesso negato all'assignment")
    if user.role == "student" and user.user_id not in doc["students"]:
        raise PermissionError("Non sei tra gli studenti assegnati")

    return Assignment(**_from_mongo(doc))

async def delete_assignment(assignment_id: str, user: UserContext) -> bool:
    if "teacher" not in user.role:
        raise PermissionError("Only teachers can delete assignments")

    deleted = await assignment_repo.delete(assignment_id)
    if not deleted:
        return False

    return True

def _from_mongo(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc
