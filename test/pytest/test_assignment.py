# test/pytest/test_assignment.py
import pytest
from datetime import datetime, timezone, timedelta

import app.services.assignment as mod
from app.schemas.assignment import AssignmentCreate, Assignment

# ---------- DOPPIO Finto: Repository ----------

class FakeRepo:
    def __init__(self):
        self.created = []
        self.deleted_ids = set()
        self.docs_by_id = {}
        self.teacher_docs = {}
        self.student_docs = {}

    async def create(self, doc):
        self.created.append(doc)
        self.docs_by_id[doc["_id"]] = doc

    async def find_for_teacher(self, teacher_id):
        return self.teacher_docs.get(teacher_id, [])

    async def find_for_student(self, student_id):
        return self.student_docs.get(student_id, [])

    async def find_one(self, assignment_id):
        return self.docs_by_id.get(assignment_id)

    async def delete(self, assignment_id):
        if assignment_id in self.docs_by_id:
            del self.docs_by_id[assignment_id]
            self.deleted_ids.add(assignment_id)
            return True
        return False


# ---------- DOPPIO Finto: UserContext (solo quello) ----------

class FakeUserContext:
    def __init__(self, user_id, role: str):
        self.user_id = user_id
        self.role = role  # "teacher" | "student" | ...


@pytest.fixture
def repo():
    return FakeRepo()


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # Manteniamo i modelli veri di AssignmentCreate e Assignment (non strettamente necessario, ma esplicito)
    monkeypatch.setattr(mod, "AssignmentCreate", AssignmentCreate, raising=True)
    monkeypatch.setattr(mod, "Assignment", Assignment, raising=True)
    # UserContext finto per evitare dipendenze da auth reale (opzionale)
    monkeypatch.setattr(mod, "UserContext", FakeUserContext, raising=True)


# ---------- TEST: create_assignment ----------

@pytest.mark.asyncio
async def test_create_assignment_happy_path(repo):
    future_deadline = datetime.now(timezone.utc) + timedelta(days=7)
    data = mod.AssignmentCreate(
        title="Compito 1",
        description="Desc",
        deadline=future_deadline,
        students=["s1", "s2"],
        content="Testo",
    )
    user = FakeUserContext(user_id="t1", role="teacher")

    new_id = await mod.create_assignment(data, user, repo=repo)
    assert new_id in repo.docs_by_id

    saved = repo.docs_by_id[new_id]
    assert saved["teacherId"] == "t1"
    assert saved["title"] == "Compito 1"
    assert saved["deadline"] == future_deadline
    assert isinstance(saved["createdAt"], datetime)
    assert saved["createdAt"].tzinfo is not None


@pytest.mark.asyncio
async def test_create_assignment_requires_teacher(repo):
    future_deadline = datetime.now(timezone.utc) + timedelta(days=7)
    data = mod.AssignmentCreate(
        title="Compito 1",
        description="Desc",
        deadline=future_deadline,
        students=["s1"],
        content="X",
    )
    user = FakeUserContext(user_id="u1", role="student")
    with pytest.raises(PermissionError):
        await mod.create_assignment(data, user, repo=repo)


# ---------- TEST: list_assignments ----------

@pytest.mark.asyncio
async def test_list_assignments_for_teacher(repo):
    repo.teacher_docs["t1"] = [
        {
            "_id": "a1",
            "teacherId": "t1",
            "title": "C1",
            "description": "D",
            "deadline": datetime.now(timezone.utc),
            "students": [],
            "content": "X",
            "createdAt": datetime.now(timezone.utc),
        }
    ]
    user = FakeUserContext(user_id="t1", role="teacher")
    items = await mod.list_assignments(user, repo=repo)
    assert len(items) == 1
    assert isinstance(items[0], mod.Assignment)
    assert items[0].id == "a1"
    assert items[0].title == "C1"


@pytest.mark.asyncio
async def test_list_assignments_for_student(repo):
    repo.student_docs["s1"] = [
        {
            "_id": "a2",
            "teacherId": "t1",
            "title": "C2",
            "description": "D",
            "deadline": datetime.now(timezone.utc),
            "students": ["s1"],
            "content": "X",
            "createdAt": datetime.now(timezone.utc),
        }
    ]
    user = FakeUserContext(user_id="s1", role="student")
    items = await mod.list_assignments(user, repo=repo)
    assert len(items) == 1
    assert isinstance(items[0], mod.Assignment)
    assert items[0].id == "a2"


@pytest.mark.asyncio
async def test_list_assignments_other_role_returns_empty(repo):
    user = FakeUserContext(user_id="x", role="admin")
    items = await mod.list_assignments(user, repo=repo)
    assert items == []


# ---------- TEST: get_assignment ----------

@pytest.mark.asyncio
async def test_get_assignment_not_found(repo):
    user = FakeUserContext(user_id="t1", role="teacher")
    assert await mod.get_assignment("missing", user, repo=repo) is None


@pytest.mark.asyncio
async def test_get_assignment_teacher_access_ok(repo):
    repo.docs_by_id["a3"] = {
        "_id": "a3",
        "teacherId": "t1",
        "title": "C3",
        "description": "D",
        "deadline": datetime.now(timezone.utc),
        "students": ["s1"],
        "content": "X",
        "createdAt": datetime.now(timezone.utc),
    }
    user = FakeUserContext(user_id="t1", role="teacher")
    item = await mod.get_assignment("a3", user, repo=repo)
    assert isinstance(item, mod.Assignment)
    assert item.id == "a3"
    assert item.title == "C3"


@pytest.mark.asyncio
async def test_get_assignment_teacher_access_denied(repo):
    repo.docs_by_id["a4"] = {
        "_id": "a4",
        "teacherId": "t1",
        "title": "C4",
        "description": "D",
        "deadline": datetime.now(timezone.utc),
        "students": [],
        "content": "X",
        "createdAt": datetime.now(timezone.utc),
    }
    user = FakeUserContext(user_id="t2", role="teacher")
    with pytest.raises(PermissionError):
        await mod.get_assignment("a4", user, repo=repo)


@pytest.mark.asyncio
async def test_get_assignment_student_access_ok(repo):
    repo.docs_by_id["a5"] = {
        "_id": "a5",
        "teacherId": "t1",
        "title": "C5",
        "description": "D",
        "deadline": datetime.now(timezone.utc),
        "students": ["s1"],
        "content": "X",
        "createdAt": datetime.now(timezone.utc),
    }
    user = FakeUserContext(user_id="s1", role="student")
    item = await mod.get_assignment("a5", user, repo=repo)
    assert isinstance(item, mod.Assignment)
    assert item.id == "a5"


@pytest.mark.asyncio
async def test_get_assignment_student_access_denied(repo):
    repo.docs_by_id["a6"] = {
        "_id": "a6",
        "teacherId": "t1",
        "title": "C6",
        "description": "D",
        "deadline": datetime.now(timezone.utc),
        "students": ["s2"],
        "content": "X",
        "createdAt": datetime.now(timezone.utc),
    }
    user = FakeUserContext(user_id="s1", role="student")
    with pytest.raises(PermissionError):
        await mod.get_assignment("a6", user, repo=repo)


# ---------- TEST: delete_assignment ----------

@pytest.mark.asyncio
async def test_delete_assignment_requires_teacher(repo):
    user = FakeUserContext(user_id="x", role="student")
    with pytest.raises(PermissionError):
        await mod.delete_assignment("a1", user, repo=repo)

@pytest.mark.asyncio
async def test_delete_assignment_ok(repo):
    repo.docs_by_id["a7"] = {
        "_id": "a7",
        "teacherId": "t1",
        "title": "C7",
        "description": "D",
        "deadline": datetime.now(timezone.utc),
        "students": [],
        "content": "X",
        "createdAt": datetime.now(timezone.utc),
    }
    user = FakeUserContext(user_id="t1", role="teacher")
    ok = await mod.delete_assignment("a7", user, repo=repo)
    assert ok is True
    assert "a7" not in repo.docs_by_id

@pytest.mark.asyncio
async def test_delete_assignment_not_found(repo):
    user = FakeUserContext(user_id="t1", role="teacher")
    ok = await mod.delete_assignment("missing", user, repo=repo)
    assert ok is False


# ---------- TEST: _from_mongo (funzione interna) ----------

def test__from_mongo_converts_id():
    doc = {
        "_id": "x1",
        "title": "C8",
        "description": "D",
        "deadline": datetime.now(timezone.utc),
        "students": [],
        "content": "X",
        "teacherId": "t1",
        "createdAt": datetime.now(timezone.utc),
    }
    out = mod._from_mongo(doc)
    assert out["id"] == "x1"
    assert "_id" not in out
