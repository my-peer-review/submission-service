from pydantic import BaseModel
from typing import List
from datetime import datetime

class FileMeta(BaseModel):
    filename: str
    path: str
    size: int

class SubmissionCreate(BaseModel):
    studentId: str
    content: str

class Submission(SubmissionCreate):
    assignmentId: str
    submissionId: str
    createdAt: datetime
    files: List[FileMeta] = []
