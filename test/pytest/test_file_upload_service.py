# tests/unit/test_file_upload_service.py
import io
import pytest
from starlette.datastructures import UploadFile, Headers

from app.schemas.submission import FileMeta
from app.schemas.context import UserContext
from app.services.file_upload_service import FileUploadService


# -------------------------- Fake storage + repo --------------------------------
class FakeStorage:
    def __init__(self):
        self.uploaded: list[dict] = []

    async def upload(self, *, filename, content_type, data, metadata):
        # consuma tutto lo stream per simulare un vero upload
        total = 0
        async for chunk in data:
            total += len(chunk)
        # traccia quanto caricato
        self.uploaded.append({
            "filename": filename, 
            "size": total, 
            "metadata": metadata,
            "content_type": content_type,
        })
        # restituisce un oggetto "StoredFile-like"
        class _Stored:
            def __init__(self, filename, size):
                self.file_id = "FAKEID"
                self.filename = filename
                self.size = size
                self.content_type = content_type
                self.checksum = "sha256:deadbeef"
                self.uri = f"gridfs://uploads/{self.file_id}"
                self.metadata = metadata
        return _Stored(filename, total)


class FakeSubmissionRepo:
    def __init__(self):
        self.files: dict[str, list[FileMeta]] = {}

    async def add_file(self, submission_id: str, file_meta: FileMeta) -> bool:
        self.files.setdefault(submission_id, []).append(file_meta)
        return True


# -------------------------------- Fixtures -------------------------------------
@pytest.fixture
def storage():
    return FakeStorage()

@pytest.fixture
def repo():
    return FakeSubmissionRepo()

@pytest.fixture
def student():
    return UserContext(user_id="s1", role="student")


# --------------------------------- Tests --------------------------------------
@pytest.mark.asyncio
async def test_upload_files_for_submission_single(storage, repo, student):
    # prepara un UploadFile in memoria
    content = b"hello world"

    upload = UploadFile(filename="test.txt",file=io.BytesIO(content),headers=Headers({"content-type": "text/plain"}))

    metas = await FileUploadService.upload_files(
        assignment_id="A1",
        submission_id="S1",
        files=[upload],
        user=student,
        repo=repo,
        storage=storage,
    )

    # ritorna una lista di FileMeta
    assert len(metas) == 1
    m = metas[0]
    assert m.filename == "test.txt"
    assert m.size == len(content)
    assert m.path.startswith("gridfs://uploads/")

    # repo.add_file è stato chiamato e ha memorizzato quel meta
    assert "S1" in repo.files and repo.files["S1"][0].filename == "test.txt"

    # storage ha registrato l'upload e i metadati
    assert storage.uploaded[0]["filename"] == "test.txt"
    assert storage.uploaded[0]["size"] == len(content)
    md = storage.uploaded[0]["metadata"]
    assert md["assignmentId"] == "A1" and md["submissionId"] == "S1" and md["studentId"] == "s1"


@pytest.mark.asyncio
async def test_upload_files_for_multiple_files(storage, repo, student):
    files = [
        UploadFile(filename="a.txt", file=io.BytesIO(b"a"), headers=Headers({"content-type": "text/plain"})),
        UploadFile(filename="b.txt", file=io.BytesIO(b"bb"), headers=Headers({"content-type": "text/plain"})),
    ]
    metas = await FileUploadService.upload_files(
        assignment_id="A1", submission_id="S1", files=files, user=student, repo=repo, storage=storage
    )
    assert [m.filename for m in metas] == ["a.txt", "b.txt"]
    assert [m.size for m in metas] == [1, 2]

@pytest.mark.asyncio
async def test_upload_pdf_content_type(storage, repo, student: UserContext):
    # PDF "finto": inizia con %PDF
    pdf_bytes = b"%PDF-1.7\n%...\n1 0 obj\n<<>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<>>\nstartxref\n0\n%%EOF\n"
    uf = UploadFile(
        filename="report.pdf",
        file=io.BytesIO(pdf_bytes),
        headers=Headers({"content-type": "application/pdf"}),  # <-- importante
    )

    metas = await FileUploadService.upload_files(
        assignment_id="A1",
        submission_id="S1",
        files=[uf],
        user=student,
        repo=repo,
        storage=storage,
    )

    assert len(metas) == 1
    m = metas[0]
    assert m.filename == "report.pdf"
    assert m.size == len(pdf_bytes)
    assert m.path.startswith("gridfs://uploads/")

    # Verifica che lo storage abbia ricevuto il content_type giusto
    up = storage.uploaded[0]
    assert up["content_type"] == "application/pdf"
    assert up["metadata"]["assignmentId"] == "A1"
    assert up["metadata"]["submissionId"] == "S1"
    assert up["metadata"]["studentId"] == student.user_id
