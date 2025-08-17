from pydantic import BaseModel
from typing import List
from datetime import datetime

class FileMeta(BaseModel):
    filename: str
    path: str
    size: int

class SubmissionCreate(BaseModel):
    assignmentId: str
    studentId: str
    content: str

class Submission(SubmissionCreate):
    submissionId: str
    createdAt: datetime
    files: List[FileMeta] = []
