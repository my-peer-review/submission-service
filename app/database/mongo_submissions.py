# app/repositories/mongo_submission.py
from datetime import datetime, timezone
from typing import Sequence, Optional
import random
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.submission_repo import SubmissionRepo
from app.schemas.submission import Submission, SubmissionCreate, FileMeta

def create_submission_id() -> str:
    return f"sm-{random.randint(0, 99999):05d}"

class MongosubmissionRepository(SubmissionRepo):
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["submissions"]

    def _from_doc(self, d: dict) -> Submission:
        return Submission(
            submissionId=d["submissionId"],
            createdAt=d["createdAt"],
            assignmentId=d["assignmentId"],
            studentId=d.get("studentId"),
            content=d.get("content", ""),
            files=[FileMeta(**f) for f in d.get("files", [])],
        )

    async def create(self, data: SubmissionCreate, *, assignment_id: str, student_id: str) -> str:
        new_id = create_submission_id()
        doc = {
            "submissionId": new_id,
            "createdAt": datetime.now(timezone.utc),
            "assignmentId": assignment_id,
            "studentId": student_id,
            "content": data.content,
            "files": [],
        }
        await self.col.insert_one(doc)
        return new_id

    async def add_file(self, submission_id: str, file_meta: FileMeta) -> bool:
        res = await self.col.update_one(
            {"submissionId": submission_id},
            {"$push": {"files": file_meta.model_dump()}}
        )
        return res.modified_count > 0

    async def find_one(self, submission_id: str) -> Optional[Submission]:
        d = await self.col.find_one({"submissionId": submission_id})
        return self._from_doc(d) if d else None

    async def find_for_assignment(self, assignment_id: str) -> Sequence[Submission]:
        cursor = self.col.find({"assignmentId": assignment_id}).sort("createdAt", -1)
        return [self._from_doc(d) async for d in cursor]

    async def find_for_assignment_and_student(self, assignment_id: str, student_id: str) -> Sequence[Submission]:
        cursor = self.col.find({"assignmentId": assignment_id, "studentId": student_id}).sort("createdAt", -1)
        return [self._from_doc(d) async for d in cursor]

    async def find_for_student(self, student_id: str) -> Sequence[Submission]:
        cursor = self.col.find({"studentId": student_id}).sort("createdAt", -1)
        return [self._from_doc(d) async for d in cursor]

    async def delete(self, submission_id: str) -> bool:
        res = await self.col.delete_one({"submissionId": submission_id})
        return res.deleted_count > 0

    async def ensure_indexes(self):
        await self.col.create_index("assignmentId")
        await self.col.create_index("studentId")
        await self.col.create_index("submissionId", unique=True)
