# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket  

from app.core.config import settings
from app.database.mongo_submissions import MongosubmissionRepository
from app.database.gridfs import GridFSStorage
from app.routers.v1 import health
from app.routers.v1 import submission

def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = AsyncIOMotorClient(settings.mongo_uri, uuidRepresentation="standard")
        db = client[settings.mongo_db_name]

        # Repo esistente
        repo = MongosubmissionRepository(db)
        await repo.ensure_indexes()
        app.state.submission_repo = repo

        # NEW: GridFS bucket + storage minimale
        bucket = AsyncIOMotorGridFSBucket(db, bucket_name="uploads", chunk_size_bytes=255 * 1024)
        app.state.binary_storage = GridFSStorage(bucket=bucket, bucket_name="uploads")

        yield
        client.close()

    app = FastAPI(
        title="submission Microservice",
        description="Microservizio per la gestione degli submission",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )

    app.include_router(health.router,     prefix="/api/v1", tags=["health"])
    app.include_router(submission.router, prefix="/api/v1", tags=["submissions"])
    return app

app = create_app()
