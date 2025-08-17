from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence, Optional
from app.schemas.submission import Submission, SubmissionCreate, FileMeta

class SubmissionRepo(ABC):
    @abstractmethod
    async def create(self, data: SubmissionCreate, *, teacher_id: str) -> str:
        """Crea una submission e ritorna l'ID generato."""
        raise NotImplementedError

    @abstractmethod
    async def add_file(self, submission_id: str, file_meta: FileMeta) -> bool:
        """Aggiunge un metadato file alla submission."""
        raise NotImplementedError

    @abstractmethod
    async def find_for_assignment(self, assignment_id: str) -> Sequence[Submission]:
        """Ritorna le submission per un dato assignment."""
        raise NotImplementedError

    @abstractmethod
    async def find_for_student(self, student_id: str) -> Sequence[Submission]:
        """Ritorna le submission per uno studente."""
        raise NotImplementedError
    
    @abstractmethod
    async def find_for_assignment_and_student(self, assignment_id: str, student_id: str) -> Sequence[Submission]:
        """Ritorna le submission per un assignment e uno studente specifico."""
        raise NotImplementedError

    @abstractmethod
    async def find_one(self, submission_id: str) -> Optional[Submission]:
        """Ritorna una submission per ID, oppure None se non esiste."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, submission_id: str) -> bool:
        """Cancella una submission."""
        raise NotImplementedError