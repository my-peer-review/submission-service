from fastapi import Request
from app.database.submission_repo import SubmissionRepo
from app.database.base import BinaryStorage

def get_repository(request: Request) -> SubmissionRepo:
    repo = getattr(request.app.state, "submission_repo", None)
    if repo is None:
        raise RuntimeError("Repository non inizializzato")
    return repo

def get_storage(request: Request) -> BinaryStorage:
    storage = getattr(request.app.state, "binary_storage", None)
    if storage is None:
        raise RuntimeError("Storage non inizializzato")
    return storage