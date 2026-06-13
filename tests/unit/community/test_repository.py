"""Unit tests for src/community/repository.py (mocked asyncpg pool)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.community.repository import ProfileRepository


def _make_pool(fetchrow_return=None, fetch_return=None):
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=fetch_return or [])
    conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    conn.execute = AsyncMock(return_value=None)

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=cm)
    return pool, conn


class TestInitSchema:
    @pytest.mark.asyncio
    async def test_executes_create_table(self):
        pool, conn = _make_pool()
        repo = ProfileRepository(pool)
        await repo.init_schema()
        conn.execute.assert_called_once()
        assert "CREATE TABLE" in conn.execute.call_args[0][0]


class TestSaveProfile:
    @pytest.mark.asyncio
    async def test_reuses_existing_fake_name(self):
        pool, conn = _make_pool(fetchrow_return={"fake_name": "נשר 42"})
        repo = ProfileRepository(pool)
        fake_name = await repo.save_profile("hash1", 10.0, 80.0, "medium", 50.0, "01/01/2025", [])
        assert fake_name == "נשר 42"

    @pytest.mark.asyncio
    async def test_generates_new_fake_name_when_none_exists(self):
        pool, conn = _make_pool(fetchrow_return=None, fetch_return=[])
        repo = ProfileRepository(pool)
        fake_name = await repo.save_profile("hash1", 10.0, 80.0, "medium", 50.0, "01/01/2025", [])
        animal, number = fake_name.rsplit(" ", 1)
        assert number.isdigit()

    @pytest.mark.asyncio
    async def test_upserts_with_rounded_values(self):
        pool, conn = _make_pool(fetchrow_return={"fake_name": "X"})
        repo = ProfileRepository(pool)
        await repo.save_profile("hash1", 12.345, 88.999, "high", 80.06, "01/01/2025", [])
        args = conn.execute.call_args[0]
        assert args[3] == 12.35   # weighted_tsua rounded
        assert args[4] == 89.0    # weighted_score rounded
        assert args[6] == 80.1    # weighted_equity_exposure rounded

    @pytest.mark.asyncio
    async def test_handles_none_equity_exposure(self):
        pool, conn = _make_pool(fetchrow_return={"fake_name": "X"})
        repo = ProfileRepository(pool)
        await repo.save_profile("hash1", 1.0, 1.0, "low", None, "01/01/2025", [])
        args = conn.execute.call_args[0]
        assert args[6] is None


class TestFetchLeaderboard:
    @pytest.mark.asyncio
    async def test_returns_rows(self):
        rows = [{"fake_name": "נשר 10"}]
        pool, conn = _make_pool(fetch_return=rows)
        repo = ProfileRepository(pool)
        result = await repo.fetch_leaderboard()
        assert result == rows


class TestFetchProfile:
    @pytest.mark.asyncio
    async def test_returns_row(self):
        row = {"fake_name": "נשר 42"}
        pool, conn = _make_pool(fetchrow_return=row)
        repo = ProfileRepository(pool)
        result = await repo.fetch_profile("נשר 42")
        assert result == row

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        pool, conn = _make_pool(fetchrow_return=None)
        repo = ProfileRepository(pool)
        result = await repo.fetch_profile("Unknown")
        assert result is None
