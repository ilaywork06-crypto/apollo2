"""Shared FastAPI dependencies for database access."""

import asyncpg
from fastapi import Depends, Request

from src.community.repository import ProfileRepository


async def get_pool(request: Request) -> asyncpg.Pool:
    """Return the application's shared asyncpg connection pool."""
    return request.app.state.pool


async def get_profile_repository(pool: asyncpg.Pool = Depends(get_pool)) -> ProfileRepository:
    """Return a :class:`ProfileRepository` bound to the shared connection pool."""
    return ProfileRepository(pool)
