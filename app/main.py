from fastapi import FastAPI

from app.api.routes import admin, auth, health, users
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.project_name)

    app.include_router(health.router)
    app.include_router(auth.router, prefix=settings.api_v1_prefix)
    app.include_router(users.router, prefix=settings.api_v1_prefix)
    app.include_router(admin.router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
