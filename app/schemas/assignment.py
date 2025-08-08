from pydantic import BaseModel
from typing import List
from datetime import datetime

# Usato in POST /assignments
class AssignmentCreate(BaseModel):
    title: str
    description: str
    deadline: datetime
    students: List[str]
    content: str

# Usato come entità completa (es. risposta o DB)
class Assignment(AssignmentCreate):
    id: str
    teacherId: str
    createdAt: datetime
