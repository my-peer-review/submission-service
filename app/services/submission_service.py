# app/services/submission.py
from typing import Sequence, Optional
from app.schemas.submission import SubmissionCreate, Submission, FileMeta
from app.schemas.context import UserContext
from app.database.submission_repo import SubmissionRepo
from app.database.base import BinaryStorage

def _is_teacher(role):
    return role == "teacher" or (isinstance(role, (list, tuple, set)) and "teacher" in role)

def _is_student(role):
    return role == "student" or (isinstance(role, (list, tuple, set)) and "student" in role)

class submissionService:
    @staticmethod
    async def create_submission(
        assignment_id: str,
        data: SubmissionCreate,
        user: UserContext,
        repo: SubmissionRepo
    ) -> str:
        if not _is_student(user.role):
            raise PermissionError("Only students can create submissions")
        data.studentId = user.user_id

        already = await repo.find_for_assignment_and_student(assignment_id, user.user_id)
        if already:
            raise PermissionError("You have already submitted for this assignment")
        else:
            return await repo.create(data, assignment_id=assignment_id, student_id=user.user_id)
        
    
    @staticmethod
    async def add_file(submission_id: str, file_meta: FileMeta, user: UserContext, repo: SubmissionRepo) -> bool:
        if not _is_student(user.role):
            raise PermissionError("Unauthorized to add files")
        return await repo.add_file(submission_id, file_meta)

    @staticmethod
    async def list_for_assignment(assignment_id: str, user: UserContext, repo: SubmissionRepo) -> Sequence[Submission]:
        if _is_teacher(user.role):
            return await repo.find_for_assignment(assignment_id)
        elif _is_student(user.role):
            return await repo.find_for_assignment_and_student(assignment_id, user.user_id)
        else:
            raise PermissionError("Unauthorized access")

    @staticmethod
    async def get_submission(submission_id: str, user: UserContext, repo: SubmissionRepo) -> Optional[Submission]:
        submission = await repo.find_one(submission_id)
        if submission is None:
            return None
        if _is_student(user.role):
            if submission.studentId != user.user_id:
                raise PermissionError("Unauthorized access to this submission")
            return submission
        if _is_teacher(user.role):
            return submission
        else:
            raise PermissionError("Unauthorized access")
        
    @staticmethod
    async def delete_submission(submission_id: str, user: UserContext, repo: SubmissionRepo, storage: BinaryStorage | None = None) -> bool:
        if not _is_teacher(user.role):
            raise PermissionError("Only teachers can delete submissions")

        # Se abbiamo lo storage, eliminiamo prima gli allegati
        if storage is not None:
            submission = await repo.find_one(submission_id)
            if submission is None:
                return False
            for f in submission.files:
                # path atteso: gridfs://<bucket>/<file_id>
                if f.path.startswith("gridfs://"):
                    file_id = f.path.rsplit("/", 1)[-1]
                    try:
                        await storage.delete(file_id)
                    except Exception:
                        # non bloccare la cancellazione della submission se un file fallisce
                        pass

        return await repo.delete(submission_id)