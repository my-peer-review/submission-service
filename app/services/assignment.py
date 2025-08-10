# app/services/assignment.py
from uuid import uuid4
from datetime import datetime, timezone
from app.schemas.assignment import AssignmentCreate, Assignment
from app.schemas.context import UserContext
from app.database.assignment_repo import assignment_repo as _default_repo

def _get_repo():
    return _default_repo

def _is_teacher(role):
    return role == "teacher" or (isinstance(role, (list, tuple, set)) and "teacher" in role)

def _is_student(role):
    return role == "student" or (isinstance(role, (list, tuple, set)) and "student" in role)

def _from_mongo(doc: dict) -> dict:
    out = dict(doc)
    out["id"] = str(out["_id"])
    out.pop("_id", None)
    return out

async def create_assignment(data: AssignmentCreate, user: UserContext, repo=None) -> str:
    if not _is_teacher(user.role):
        raise PermissionError("Only teachers can create assignments")
    repo = repo or _get_repo()

    new_id = str(uuid4())
    assignment_dict = {
        "_id": new_id,
        "createdAt": datetime.now(timezone.utc),
        "teacherId": user.user_id,
        **data.model_dump(),
    }
    await repo.create(assignment_dict)
    return new_id

async def list_assignments(user: UserContext, repo=None):
    repo = repo or _get_repo()
    if _is_teacher(user.role):
        docs = await repo.find_for_teacher(user.user_id)
    elif _is_student(user.role):
        docs = await repo.find_for_student(user.user_id)
    else:
        return []
    return [Assignment(**_from_mongo(d)) for d in docs]

async def get_assignment(assignment_id: str, user: UserContext, repo=None):
    repo = repo or _get_repo()
    doc = await repo.find_one(assignment_id)
    if not doc:
        return None
    if _is_teacher(user.role) and doc.get("teacherId") != user.user_id:
        raise PermissionError("Accesso negato all'assignment")
    if _is_student(user.role) and user.user_id not in doc.get("students", []):
        raise PermissionError("Non sei tra gli studenti assegnati")
    return Assignment(**_from_mongo(doc))

async def delete_assignment(assignment_id: str, user: UserContext, repo=None) -> bool:
    if not _is_teacher(user.role):
        raise PermissionError("Only teachers can delete assignments")
    repo = repo or _get_repo()
    return await repo.delete(assignment_id)
