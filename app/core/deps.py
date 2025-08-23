from fastapi import Request
from app.database.submission_repo import SubmissionRepo
from app.database.base import BinaryStorage
from app.services.publisher_service import SubmissionPublisher

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

def get_publisher(request: Request) -> SubmissionPublisher:
    publisher = getattr(request.app.state, "submission_publisher", None)
    if publisher is None:
        raise RuntimeError("Publiscer non inizializzato")
    return publisher