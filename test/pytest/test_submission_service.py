# tests/unit/test_submission_service.py
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.services.submission_service import submissionService
from app.schemas.submission import SubmissionCreate, Submission, FileMeta
from app.schemas.context import UserContext


# ------------------------- Fake repository (minimale) -------------------------
class FakeSubmissionRepo:
    def __init__(self):
        self.items: dict[str, Submission] = {}

    async def create(self, data: SubmissionCreate, *, assignment_id: str, student_id: str) -> str:
        new_id = str(uuid4())
        sub = Submission(
            submissionId=new_id,
            assignmentId=assignment_id,
            studentId=student_id,
            content=data.content,
            files=[],
            createdAt=datetime.now(timezone.utc),
        )
        self.items[new_id] = sub
        return new_id

    async def add_file(self, submission_id: str, file_meta: FileMeta) -> bool:
        sub = self.items.get(submission_id)
        if not sub:
            return False
        sub.files.append(file_meta)
        return True

    async def find_for_assignment(self, assignment_id: str):
        return [s for s in self.items.values() if s.assignmentId == assignment_id]

    async def find_for_assignment_and_student(self, assignment_id: str, student_id: str):
        return [s for s in self.items.values() if s.assignmentId == assignment_id and s.studentId == student_id]

    async def find_one(self, submission_id: str):
        return self.items.get(submission_id)

    async def delete(self, submission_id: str):
        return self.items.pop(submission_id, None) is not None


# ------------------------------- Fake storage ---------------------------------
class FakeStorage:
    def __init__(self):
        self.deleted: list[str] = []

    async def delete(self, file_id: str) -> bool:
        self.deleted.append(file_id)
        return True


# ------------------------------- Fixtures -------------------------------------
@pytest.fixture
def repo():
    return FakeSubmissionRepo()

@pytest.fixture
def student():
    return UserContext(user_id="s1", role="student")

@pytest.fixture
def student2():
    return UserContext(user_id="s2", role="student")

@pytest.fixture
def teacher():
    return UserContext(user_id="t1", role="teacher")

def _make_create(**overrides):
    base = dict(
        assignmentId="A1",   # richiesti dallo schema
        studentId="s1",      # (verranno sovrascritti dal service)
        content="Hello world"
    )
    base.update(overrides)
    return SubmissionCreate(**base)

# --------------------------------- Tests --------------------------------------
@pytest.mark.asyncio
async def test_create_requires_student(repo, teacher):
    with pytest.raises(PermissionError):
        await submissionService.create_submission("A1", _make_create(), teacher, repo)

@pytest.mark.asyncio
async def test_create_ok(repo, student):
    new_id = await submissionService.create_submission("A1", _make_create(), student, repo)
    assert new_id
    saved = await repo.find_one(new_id)
    assert saved is not None
    assert saved.assignmentId == "A1"
    assert saved.studentId == "s1"
    assert saved.files == []

@pytest.mark.asyncio
async def test_add_file_requires_student(repo, teacher, student):
    # crea submission come studente
    sid = await submissionService.create_submission("A1", _make_create(), student, repo)
    # tentativo docente -> vietato
    with pytest.raises(PermissionError):
        await submissionService.add_file(sid, FileMeta(filename="x.txt", path="gridfs://uploads/abc", size=1), teacher, repo)

@pytest.mark.asyncio
async def test_add_file_ok(repo, student):
    sid = await submissionService.create_submission("A1", _make_create(), student, repo)
    ok = await submissionService.add_file(
        sid, FileMeta(filename="x.txt", path="gridfs://uploads/abc123", size=3), student, repo
    )
    assert ok is True
    saved = await repo.find_one(sid)
    assert len(saved.files) == 1
    assert saved.files[0].filename == "x.txt"

@pytest.mark.asyncio
async def test_list_for_assignment_teacher_vs_student(repo, teacher, student, student2):
    # seed: due submission di studenti diversi
    sid1 = await submissionService.create_submission("A1", _make_create(), student, repo)
    sid2 = await submissionService.create_submission("A1", _make_create(), student2, repo)

    # docente vede entrambe
    items_t = await submissionService.list_for_assignment("A1", teacher, repo)
    ids_t = {s.submissionId for s in items_t}
    assert {sid1, sid2}.issubset(ids_t)

    # studente vede solo la propria
    items_s1 = await submissionService.list_for_assignment("A1", student, repo)
    assert [s.submissionId for s in items_s1] == [sid1]

@pytest.mark.asyncio
async def test_get_submission_access(repo, teacher, student, student2):
    sid = await submissionService.create_submission("A1", _make_create(), student, repo)

    # il proprietario può leggere
    mine = await submissionService.get_submission(sid, student, repo)
    assert mine is not None

    # un altro studente NO
    with pytest.raises(PermissionError):
        await submissionService.get_submission(sid, student2, repo)

    # il docente SÌ
    teach = await submissionService.get_submission(sid, teacher, repo)
    assert teach is not None

@pytest.mark.asyncio
async def test_delete_requires_teacher(repo, student):
    with pytest.raises(PermissionError):
        await submissionService.delete_submission("not-exists", student, repo, storage=FakeStorage())

@pytest.mark.asyncio
async def test_delete_ok_and_calls_storage(repo, teacher, student):
    # crea submission con un file per verificare la delete su storage
    sid = await submissionService.create_submission("A1", _make_create(), student, repo)
    # aggiungi un file con path gridfs://<bucket>/<id> (serve per estrarre file_id)
    await submissionService.add_file(
        sid, FileMeta(filename="x.txt", path="gridfs://uploads/DEADBEEF", size=1), student, repo
    )

    storage = FakeStorage()
    ok = await submissionService.delete_submission(sid, teacher, repo, storage=storage)
    assert ok is True
    # storage.delete chiamato con ID corretto
    assert storage.deleted == ["DEADBEEF"]
    # seconda delete -> False
    ok2 = await submissionService.delete_submission(sid, teacher, repo, storage=storage)
    assert ok2 is False
