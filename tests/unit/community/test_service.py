"""Unit tests for src/community/service.py (mocked ProfileRepository)."""

from unittest.mock import AsyncMock

import pytest

from src.community.service import get_leaderboard, get_profile, join_community


def _sample_funds(risk_levels=("medium", "high"), amounts=(50000, 80000)):
    return [
        {
            "name": f"Fund {i}",
            "id": str(1000 + i),
            "risk_level": risk_levels[i],
            "tsua_1": 10.0 + i,
            "grade": 70.0 + i * 5,
            "amount": amounts[i],
            "equity_exposure": 50.0 + i * 10,
        }
        for i in range(len(risk_levels))
    ]


class TestJoinCommunity:
    @pytest.mark.asyncio
    async def test_returns_success_true(self):
        repo = AsyncMock()
        repo.save_profile = AsyncMock(return_value="נשר 42")
        result = await join_community(repo, "client_1", _sample_funds())
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_profile_uses_fake_name_from_repo(self):
        repo = AsyncMock()
        repo.save_profile = AsyncMock(return_value="נשר 42")
        result = await join_community(repo, "client_1", _sample_funds())
        assert result["profile"]["fake_name"] == "נשר 42"

    @pytest.mark.asyncio
    async def test_weighted_tsua_is_float(self):
        repo = AsyncMock()
        repo.save_profile = AsyncMock(return_value="X")
        result = await join_community(repo, "c", _sample_funds())
        assert isinstance(result["profile"]["weighted_tsua"], float)

    @pytest.mark.asyncio
    async def test_weighted_tsua_calculated_correctly(self):
        repo = AsyncMock()
        repo.save_profile = AsyncMock(return_value="X")
        funds = _sample_funds()
        total = sum(f["amount"] for f in funds)
        expected = sum(f["tsua_1"] * f["amount"] / total for f in funds)
        result = await join_community(repo, "c", funds)
        assert abs(result["profile"]["weighted_tsua"] - round(expected, 2)) < 1e-6

    @pytest.mark.asyncio
    async def test_dominant_risk_is_highest_pct_risk(self):
        repo = AsyncMock()
        repo.save_profile = AsyncMock(return_value="X")
        funds = _sample_funds(
            risk_levels=("medium", "medium", "high"),
            amounts=(40000, 40000, 20000),
        )
        result = await join_community(repo, "c", funds)
        assert result["profile"]["dominant_risk"] == "medium"

    @pytest.mark.asyncio
    async def test_total_amount_zero_does_not_crash(self):
        repo = AsyncMock()
        repo.save_profile = AsyncMock(return_value="X")
        funds = _sample_funds(amounts=(0, 0))
        result = await join_community(repo, "c", funds)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_funds_json_contains_name_id_pct(self):
        repo = AsyncMock()
        repo.save_profile = AsyncMock(return_value="X")
        result = await join_community(repo, "c", _sample_funds())
        for entry in result["profile"]["funds"]:
            assert "name" in entry
            assert "id" in entry
            assert "pct" in entry

    @pytest.mark.asyncio
    async def test_passes_computed_values_to_repository(self):
        repo = AsyncMock()
        repo.save_profile = AsyncMock(return_value="X")
        await join_community(repo, "c", _sample_funds())
        repo.save_profile.assert_awaited_once()


class TestGetLeaderboard:
    def _mock_rows(self):
        return [
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

    @pytest.mark.asyncio
    async def test_returns_profiles_list(self):
        repo = AsyncMock()
        repo.fetch_leaderboard = AsyncMock(return_value=self._mock_rows())
        result = await get_leaderboard(repo)
        assert "profiles" in result
        assert len(result["profiles"]) == 2

    @pytest.mark.asyncio
    async def test_profile_has_num_funds(self):
        repo = AsyncMock()
        repo.fetch_leaderboard = AsyncMock(return_value=self._mock_rows())
        result = await get_leaderboard(repo)
        assert result["profiles"][0]["num_funds"] == 1

    @pytest.mark.asyncio
    async def test_joined_short_format(self):
        repo = AsyncMock()
        repo.fetch_leaderboard = AsyncMock(return_value=self._mock_rows())
        result = await get_leaderboard(repo)
        assert result["profiles"][0]["joined"] == "01/2025"


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        repo = AsyncMock()
        repo.fetch_profile = AsyncMock(return_value=None)
        result = await get_profile(repo, "Unknown 99")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_profile_dict(self):
        repo = AsyncMock()
        repo.fetch_profile = AsyncMock(return_value={
            "fake_name": "נשר 42", "weighted_tsua": 11.0, "weighted_score": 80.0,
            "dominant_risk": "medium", "weighted_equity_exposure": 55.0,
            "joined": "10/04/2025", "funds": '[{"name":"F","id":"1","pct":100.0}]',
        })
        result = await get_profile(repo, "נשר 42")
        assert result is not None
        assert result["fake_name"] == "נשר 42"
        assert result["dominant_risk"] == "medium"

    @pytest.mark.asyncio
    async def test_funds_parsed_from_json_string(self):
        repo = AsyncMock()
        repo.fetch_profile = AsyncMock(return_value={
            "fake_name": "X", "weighted_tsua": 0.0, "weighted_score": 0.0,
            "dominant_risk": "low", "weighted_equity_exposure": None,
            "joined": "01/01/2025", "funds": '[{"name":"Fund1","id":"10","pct":100.0}]',
        })
        result = await get_profile(repo, "X")
        assert isinstance(result["funds"], list)
        assert result["funds"][0]["name"] == "Fund1"
