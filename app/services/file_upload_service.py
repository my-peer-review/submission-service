# app/services/file_upload_service.py
from __future__ import annotations

from asyncio import Protocol
from typing import AsyncIterator, Iterable, Optional

from app.schemas.submission import FileMeta
from app.schemas.context import UserContext
from app.database.base import BinaryStorage
from app.database.submission_repo import SubmissionRepo
from app.services.submission_service import submissionService

READ_CHUNK = 1024 * 1024  # 1MB

# Qualsiasi oggetto che somigli a UploadFile:
class UploadFileLike(Protocol):
    filename: str
    content_type: Optional[str]
    async def read(self, size: int = ...) -> bytes: ...

class FileUploadService:
    @staticmethod
    async def _iter_file(f: UploadFileLike, chunk_size: int = READ_CHUNK) -> AsyncIterator[bytes]:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            yield chunk

    @classmethod
    async def upload_files(
        cls,
        *,
        assignment_id: str,
        submission_id: str,
        files: Iterable[UploadFileLike],
        user: UserContext,
        repo: SubmissionRepo,
        storage: BinaryStorage,
    ) -> list[FileMeta]:
        metas: list[FileMeta] = []
        for f in files:
            stored = await storage.upload(
                filename=f.filename,
                content_type=f.content_type,
                data=cls._iter_file(f),
                metadata={
                    "studentId": user.user_id,
                    "assignmentId": assignment_id,
                    "submissionId": submission_id,
                },
            )
            fm = FileMeta(
                filename=stored.filename,
                path=stored.uri,
                size=stored.size,
            )
            metas.append(fm)

            await submissionService.add_file(submission_id, fm, user, repo)
        return metas
