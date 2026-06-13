"""FastAPI application factory for the Apollo fund comparison service."""

import os
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import comparison, community, health
from src.community.repository import ProfileRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await asyncpg.create_pool(
        os.environ.get("DATABASE_URL", "postgresql://apollo:apollo@localhost:5432/apollo")
    )
    await ProfileRepository(pool).init_schema()
    app.state.pool = pool
    yield
    await pool.close()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(comparison.router)
    app.include_router(community.router)
    return app


APP = create_app()


if __name__ == "__main__":
    uvicorn.run("src.api.app:APP", host="127.0.0.1", port=8000, reload=True)
