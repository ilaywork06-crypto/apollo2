"""Unit tests for src/community.py (pure functions and mocked DB)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.community import _hash_client_id, get_leaderboard, get_profile, join_community


# ---------------------------------------------------------------------------
# _hash_client_id
# ---------------------------------------------------------------------------


class TestHashClientId:
    def test_deterministic(self):
        assert _hash_client_id("123456789") == _hash_client_id("123456789")

    def test_different_ids_give_different_hashes(self):
        assert _hash_client_id("111111111") != _hash_client_id("222222222")

    def test_returns_64_char_hex_string(self):
        result = _hash_client_id("test_id")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_sensitive_to_case(self):
        assert _hash_client_id("ABC") != _hash_client_id("abc")


# ---------------------------------------------------------------------------
# join_community (mocked pool)
# ---------------------------------------------------------------------------


def _make_pool(existing_fake_name=None):
    """Create a mock asyncpg pool with a simple in-memory state."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(
        return_value={"fake_name": existing_fake_name} if existing_fake_name else None
    )
    conn.execute = AsyncMock(return_value=None)

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=cm)
    return pool, conn


def _sample_funds(risk_levels=("medium", "high"), amounts=(50000, 80000)):
    return [
        {
            "name": f"Fund {i}",
            "id": str(1000 + i),
            "risk_level": risk_levels[i],
            "tsua_1": 10.0 + i,
            "grade": 70.0 + i * 5,
            "amount": amounts[i],
            "pct_of_total": 0.0,
            "equity_exposure": 50.0 + i * 10,
        }
        for i in range(len(risk_levels))
    ]


class TestJoinCommunity:
    @pytest.mark.asyncio
    async def test_returns_success_true(self):
        pool, _ = _make_pool()
        result = await join_community(pool, "client_1", _sample_funds())
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_profile_has_fake_name(self):
        pool, _ = _make_pool()
        result = await join_community(pool, "client_1", _sample_funds())
        assert "fake_name" in result["profile"]

    @pytest.mark.asyncio
    async def test_existing_profile_keeps_same_fake_name(self):
        pool, _ = _make_pool(existing_fake_name="נשר 42")
        result = await join_community(pool, "client_1", _sample_funds())
        assert result["profile"]["fake_name"] == "נשר 42"

    @pytest.mark.asyncio
    async def test_weighted_tsua_is_float(self):
        pool, _ = _make_pool()
        result = await join_community(pool, "c", _sample_funds())
        assert isinstance(result["profile"]["weighted_tsua"], float)

    @pytest.mark.asyncio
    async def test_weighted_tsua_calculated_correctly(self):
        # Two funds: 50k (37.5%) at 10%, 80k (62.5 %) at 11%
        pool, _ = _make_pool()
        funds = _sample_funds()
        total = sum(f["amount"] for f in funds)
        expected = sum(f["tsua_1"] * f["amount"] / total for f in funds)
        result = await join_community(pool, "c", funds)
        assert abs(result["profile"]["weighted_tsua"] - round(expected, 2)) < 1e-6

    @pytest.mark.asyncio
    async def test_dominant_risk_is_highest_pct_risk(self):
        # 3 funds: 2 medium, 1 high → dominant = medium
        funds = _sample_funds(
            risk_levels=("medium", "medium", "high"),
            amounts=(40000, 40000, 20000),
        )
        pool, _ = _make_pool()
        result = await join_community(pool, "c", funds)
        assert result["profile"]["dominant_risk"] == "medium"

    @pytest.mark.asyncio
    async def test_total_amount_zero_does_not_crash(self):
        funds = _sample_funds(amounts=(0, 0))
        pool, _ = _make_pool()
        result = await join_community(pool, "c", funds)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_equity_exposure_computed(self):
        pool, _ = _make_pool()
        result = await join_community(pool, "c", _sample_funds())
        # Should be a float or None; not an error
        exp = result["profile"]["weighted_equity_exposure"]
        assert exp is None or isinstance(exp, float)

    @pytest.mark.asyncio
    async def test_funds_json_contains_name_id_pct(self):
        pool, _ = _make_pool()
        result = await join_community(pool, "c", _sample_funds())
        for entry in result["profile"]["funds"]:
            assert "name" in entry
            assert "id" in entry
            assert "pct" in entry


# ---------------------------------------------------------------------------
# get_leaderboard (mocked pool)
# ---------------------------------------------------------------------------


class TestGetLeaderboard:
    def _mock_rows(self):
        rows = [
            {
                "fake_name": "נשר 10",
                "weighted_tsua": 12.5,
                "weighted_score": 88.0,
                "dominant_risk": "high",
                "weighted_equity_exposure": 80.0,
                "funds": '[{"name":"F","id":"1","pct":100.0}]',
                "joined": "01/01/2025",
            },
            {
                "fake_name": "דוב 20",
                "weighted_tsua": 8.0,
                "weighted_score": 75.0,
                "dominant_risk": "medium",
                "weighted_equity_exposure": 45.0,
                "funds": '[{"name":"G","id":"2","pct":100.0}]',
                "joined": "05/03/2025",
            },
        ]
        return rows

    @pytest.mark.asyncio
    async def test_returns_profiles_list(self):
        rows = self._mock_rows()
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=rows)
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=False)
        pool = MagicMock()
        pool.acquire = MagicMock(return_value=cm)

        result = await get_leaderboard(pool)
        assert "profiles" in result
        assert len(result["profiles"]) == 2

    @pytest.mark.asyncio
    async def test_profile_has_num_funds(self):
        rows = self._mock_rows()
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=rows)
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=False)
        pool = MagicMock()
        pool.acquire = MagicMock(return_value=cm)

        result = await get_leaderboard(pool)
        assert result["profiles"][0]["num_funds"] == 1

    @pytest.mark.asyncio
    async def test_joined_short_format(self):
        rows = self._mock_rows()
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=rows)
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=False)
        pool = MagicMock()
        pool.acquire = MagicMock(return_value=cm)

        result = await get_leaderboard(pool)
        # "01/01/2025" → "01/2025"
        assert result["profiles"][0]["joined"] == "01/2025"


# ---------------------------------------------------------------------------
# get_profile (mocked pool)
# ---------------------------------------------------------------------------


class TestGetProfile:
    def _pool_with_row(self, row):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=row)
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=False)
        pool = MagicMock()
        pool.acquire = MagicMock(return_value=cm)
        return pool

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        pool = self._pool_with_row(None)
        result = await get_profile(pool, "Unknown 99")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_profile_dict(self):
        row = {
            "fake_name": "נשר 42",
            "weighted_tsua": 11.0,
            "weighted_score": 80.0,
            "dominant_risk": "medium",
            "weighted_equity_exposure": 55.0,
            "joined": "10/04/2025",
            "funds": '[{"name":"F","id":"1","pct":100.0}]',
        }
        pool = self._pool_with_row(row)
        result = await get_profile(pool, "נשר 42")
        assert result is not None
        assert result["fake_name"] == "נשר 42"
        assert result["dominant_risk"] == "medium"

    @pytest.mark.asyncio
    async def test_funds_parsed_from_json_string(self):
        row = {
            "fake_name": "X",
            "weighted_tsua": 0.0,
            "weighted_score": 0.0,
            "dominant_risk": "low",
            "weighted_equity_exposure": None,
            "joined": "01/01/2025",
            "funds": '[{"name":"Fund1","id":"10","pct":100.0}]',
        }
        pool = self._pool_with_row(row)
        result = await get_profile(pool, "X")
        assert isinstance(result["funds"], list)
        assert result["funds"][0]["name"] == "Fund1"
