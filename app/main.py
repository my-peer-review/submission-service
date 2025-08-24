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
from app.services.publisher_service import SubmissionPublisher

def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = AsyncIOMotorClient(settings.mongo_uri, uuidRepresentation="standard")
        db = client[settings.mongo_db_name]

        # Mongo repository
        repo = MongosubmissionRepository(db)
        await repo.ensure_indexes()
        app.state.submission_repo = repo

        # GridFS bucket
        bucket = AsyncIOMotorGridFSBucket(db, bucket_name="uploads", chunk_size_bytes=255 * 1024)
        app.state.binary_storage = GridFSStorage(bucket=bucket, bucket_name="uploads")

        # --- RabbitMQ Publisher ---
        publisher = SubmissionPublisher(
            rabbitmq_url=settings.rabbitmq_url,
            heartbeat= 30,
            review_exchange="elearning.submissions-consegnate",
            review_routing_key="submissions.reviews",
            report_exchange = "elearning.reports",
            report_routing_key = "submissions.reports",
        )

        await publisher.connect(max_retries=10, delay=5)
        app.state.submission_publisher = publisher

        try:
            yield
        finally:
            try:
                await publisher.close()
            finally:
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
