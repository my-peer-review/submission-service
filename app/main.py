from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.v1 import assignment_router, health_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Assignment Microservice",
        description="Microservizio per la gestione degli assignment",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router.router, prefix="/api/v1", tags=["health"])

    app.include_router(assignment_router.router, prefix="/api/v1/assignments", tags=["Assignments"])

    return app

app = create_app()
