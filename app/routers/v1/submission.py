from datetime import datetime
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.schemas.submission import SubmissionCreate, Submission, FileMeta
from app.schemas.context import UserContext

from app.core.deps import get_repository, get_storage, get_publisher

from app.services.submission_service import submissionService
from app.services.auth_service import AuthService
from app.services.file_upload_service import FileUploadService
from app.services.publisher_service import SubmissionPublisher

from app.database.submission_repo import SubmissionRepo
from app.database.base import BinaryStorage

router = APIRouter()

SubmissionRepoDep = Annotated[SubmissionRepo, Depends(get_repository)]
FileStorageDep    = Annotated[BinaryStorage, Depends(get_storage)]
PublisherDep      = Annotated[SubmissionPublisher, Depends(get_publisher)]

CurrentUser       = Annotated[UserContext, Depends(AuthService.get_current_user)]


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def create_submission_for_assignment_endpoint(
    user: CurrentUser,
    repo: SubmissionRepoDep,
    storage: FileStorageDep,
    publisher: PublisherDep,
    request: Request,
    content: Annotated[str, Form(..., alias="content")],
    assignment_id: Annotated[str, Form(..., alias="assignmentId")],
    files: Annotated[Optional[List[UploadFile]], File()] = None
):
    try:
        payload = SubmissionCreate(
            assignmentId=assignment_id,
            studentId=user.user_id,
            content=content,
        )
        new_id = await submissionService.create_submission(
            assignment_id, payload, user, repo
        )

        safe_files: List[UploadFile] = [
            f for f in (files or [])
            if f is not None and getattr(f, "filename", None) not in (None, "")
        ]
        if safe_files:
            metas: list[FileMeta] = await FileUploadService.upload_files(
                assignment_id=assignment_id,
                submission_id=new_id,
                files=safe_files, 
                user=user,
                repo=repo,
                storage=storage,
            )
        else:
            metas = []

        try:
            await publisher.publish_submission_delivered(
                submission_id=new_id,
                assignment_id=assignment_id,
                student_id = user.user_id,
                delivered_at = datetime.now()
            )
        except Exception as e:
            admin = UserContext(user_id="admin", role= "teacher")
            await submissionService.delete_submission(new_id, admin, repo, storage=storage)
            raise HTTPException(status_code=503, detail=f"Invio evento RabbitMQ fallito: {e}")

        # 4) risposta OK
        files_payload: list[dict] = []
        for m in metas:
            path = getattr(m, "path", None)
            filename = getattr(m, "filename", None)
            file_id = path.split("/")[-1] if isinstance(path, str) and path.startswith("gridfs://") else None
            download_url = str(request.url_for("download_file", file_id=file_id)) if file_id else None
            if filename and download_url:
                files_payload.append({"filename": filename, "downloadUrl": download_url})

        location = f"/api/v1/submissions/{assignment_id}/{new_id}"
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "submission created",
                "submissionId": new_id,
                "assignmentId": assignment_id,
                "files": files_payload,
            },
            headers={"Location": location},
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.get("/files/{file_id}", name="download_file")
async def download_file(file_id: str, storage: FileStorageDep):
    info = await storage.info(file_id)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")

    async def body():
        async for chunk in storage.stream(file_id):
            yield chunk

    return StreamingResponse(
        body(),
        headers={
            "Content-Disposition": f'attachment; filename="{info.filename or file_id}"',
            "Content-Type": info.content_type or "application/octet-stream",
        },
    )

@router.get("/assignments/{assignment_id}/submissions", response_model=list[Submission])
async def list_submissions_endpoint(
    assignment_id: str,
    user: CurrentUser,
    repo: SubmissionRepoDep,
):
    try:
        return await submissionService.list_for_assignment(assignment_id, user, repo)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
# DETTAGLIO
@router.get("/submissions/{submission_id}", response_model=Submission | None)
async def get_submission_endpoint(
    submission_id: str,
    user: CurrentUser,
    repo: SubmissionRepoDep,
):
    try:
        result = await submissionService.get_submission(submission_id, user, repo)
        if result is None:
            raise HTTPException(status_code=404, detail="submission not found")
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

# DELETE (solo docente)
@router.delete("/submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission_endpoint(
    submission_id: str,
    user: CurrentUser,
    repo: SubmissionRepoDep,
    storage: FileStorageDep,
):
    try:
        deleted = await submissionService.delete_submission(submission_id, user, repo, storage=storage)
        if not deleted:
            raise HTTPException(status_code=404, detail="submission not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))