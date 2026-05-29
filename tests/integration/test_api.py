"""Integration tests for the FastAPI endpoints.

The database pool is mocked so no real PostgreSQL connection is required.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from src.api.app import APP


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pool():
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=cm)
    pool.close = AsyncMock()
    return pool, conn


@pytest.fixture(scope="module")
def client():
    mock_pool, _ = _make_pool()
    with (
        patch("asyncpg.create_pool", AsyncMock(return_value=mock_pool)),
        patch("src.community.init_db", AsyncMock()),
        TestClient(APP) as c,
    ):
        yield c


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_ok_status(self, client):
        resp = client.get("/health")
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /compare
# ---------------------------------------------------------------------------


class TestCompare:
    _MOCK_RESULT = {
        "funds": [
            {
                "client": {
                    "name": "Fund Alpha",
                    "id": "103",
                    "grade": 72.5,
                    "rank": 3,
                    "total_in_risk": 20,
                    "risk_level": "medium",
                    "amount": 150000.0,
                    "dmei_nihul": 0.5,
                    "tsua_1": 18.98,
                    "tsua_3": 10.0,
                    "tsua_5": 9.0,
                    "hevra": "מיטב",
                    "seniority_date": "01/01/2020",
                    "percentile": 85,
                    "equity_exposure": 46.44,
                    "client_id": "987654321",
                    "default_grade": 70.0,
                },
                "alternatives": [],
                "golden": {},
            }
        ]
    }

    _MISLAKA_XML = """\
<MislakaRoot>
  <YeshutLakoach>
    <MISPAR-ZIHUY-LAKOACH>987654321</MISPAR-ZIHUY-LAKOACH>
  </YeshutLakoach>
  <Mutzar>
    <KOD-MEZAHE-YATZRAN>Yatzran1</KOD-MEZAHE-YATZRAN>
    <HeshbonOPolisa>
      <SHEM-TOCHNIT>Plan A</SHEM-TOCHNIT>
      <TAARICH-HITZTARFUT-MUTZAR>01/01/2020</TAARICH-HITZTARFUT-MUTZAR>
      <PirteiTaktziv>
        <PerutMasluleiHashkaa>
          <SCHUM-TZVIRA-BAMASLUL>150000.0</SCHUM-TZVIRA-BAMASLUL>
          <KOD-MASLUL-HASHKAA>XX000103</KOD-MASLUL-HASHKAA>
          <SHEUR-DMEI-NIHUL-HISACHON>0.5</SHEUR-DMEI-NIHUL-HISACHON>
        </PerutMasluleiHashkaa>
      </PirteiTaktziv>
    </HeshbonOPolisa>
  </Mutzar>
</MislakaRoot>
"""

    def test_returns_200_with_mocked_engine(self, client):
        with patch("src.api.app.run_comparison", return_value=self._MOCK_RESULT):
            resp = client.post(
                "/compare",
                data={
                    "weight_1": "10",
                    "weight_3": "20",
                    "weight_5": "25",
                    "weight_sharp": "45",
                    "low_exposure_threshold": "25",
                    "medium_exposure_threshold": "75",
                },
                files=[("mislaka_file", ("test.xml", self._MISLAKA_XML.encode(), "text/xml"))],
            )
        assert resp.status_code == 200

    def test_response_has_funds_key(self, client):
        with patch("src.api.app.run_comparison", return_value=self._MOCK_RESULT):
            resp = client.post(
                "/compare",
                data={
                    "weight_1": "10",
                    "weight_3": "20",
                    "weight_5": "25",
                    "weight_sharp": "45",
                    "low_exposure_threshold": "25",
                    "medium_exposure_threshold": "75",
                },
                files=[("mislaka_file", ("test.xml", self._MISLAKA_XML.encode(), "text/xml"))],
            )
        assert "funds" in resp.json()

    def test_engine_called_with_correct_weights(self, client):
        with patch("src.api.app.run_comparison", return_value={"funds": []}) as mock_engine:
            client.post(
                "/compare",
                data={
                    "weight_1": "10",
                    "weight_3": "20",
                    "weight_5": "25",
                    "weight_sharp": "45",
                    "low_exposure_threshold": "25",
                    "medium_exposure_threshold": "75",
                },
                files=[("mislaka_file", ("test.xml", self._MISLAKA_XML.encode(), "text/xml"))],
            )
        _, kwargs = mock_engine.call_args
        assert kwargs["weight_1"] == 10
        assert kwargs["weight_3"] == 20
        assert kwargs["weight_5"] == 25
        assert kwargs["weight_sharp"] == 45

    def test_missing_file_returns_422(self, client):
        resp = client.post(
            "/compare",
            data={"weight_1": "10", "weight_3": "20", "weight_5": "25", "weight_sharp": "45",
                  "low_exposure_threshold": "25", "medium_exposure_threshold": "75"},
        )
        assert resp.status_code == 422

    def test_multiple_files_accepted(self, client):
        with patch("src.api.app.run_comparison", return_value={"funds": []}) as mock_engine:
            client.post(
                "/compare",
                data={
                    "weight_1": "10",
                    "weight_3": "20",
                    "weight_5": "25",
                    "weight_sharp": "45",
                    "low_exposure_threshold": "25",
                    "medium_exposure_threshold": "75",
                },
                files=[
                    ("mislaka_file", ("f1.xml", self._MISLAKA_XML.encode(), "text/xml")),
                    ("mislaka_file", ("f2.xml", self._MISLAKA_XML.encode(), "text/xml")),
                ],
            )
        _, kwargs = mock_engine.call_args
        assert len(kwargs["mislaka_file"]) == 2

    def test_bad_hevrot_passed_through(self, client):
        with patch("src.api.app.run_comparison", return_value={"funds": []}) as mock_engine:
            client.post(
                "/compare",
                data={
                    "weight_1": "10",
                    "weight_3": "20",
                    "weight_5": "25",
                    "weight_sharp": "45",
                    "low_exposure_threshold": "25",
                    "medium_exposure_threshold": "75",
                    "bad_hevrot": ["הפועלים", "לאומי"],
                },
                files=[("mislaka_file", ("test.xml", self._MISLAKA_XML.encode(), "text/xml"))],
            )
        _, kwargs = mock_engine.call_args
        assert "הפועלים" in kwargs["bad_hevrot"]

    def test_override_risk_level_passed_through(self, client):
        with patch("src.api.app.run_comparison", return_value={"funds": []}) as mock_engine:
            client.post(
                "/compare",
                data={
                    "weight_1": "10",
                    "weight_3": "20",
                    "weight_5": "25",
                    "weight_sharp": "45",
                    "low_exposure_threshold": "25",
                    "medium_exposure_threshold": "75",
                    "override_risk_level": "high",
                },
                files=[("mislaka_file", ("test.xml", self._MISLAKA_XML.encode(), "text/xml"))],
            )
        _, kwargs = mock_engine.call_args
        assert kwargs["override_risk_level"] == "high"


# ---------------------------------------------------------------------------
# /community/leaderboard
# ---------------------------------------------------------------------------


class TestCommunityLeaderboard:
    def test_returns_200(self, client):
        with patch("src.api.app.get_leaderboard", AsyncMock(return_value={"profiles": []})):
            resp = client.get("/community/leaderboard")
        assert resp.status_code == 200

    def test_returns_profiles_key(self, client):
        with patch("src.api.app.get_leaderboard", AsyncMock(return_value={"profiles": []})):
            resp = client.get("/community/leaderboard")
        assert "profiles" in resp.json()


# ---------------------------------------------------------------------------
# /community/profile/{fake_name}
# ---------------------------------------------------------------------------


class TestCommunityProfile:
    def test_returns_404_for_unknown_profile(self, client):
        with patch("src.api.app.get_profile", AsyncMock(return_value=None)):
            resp = client.get("/community/profile/Unknown%2099")
        assert resp.status_code == 404

    def test_returns_profile_when_found(self, client):
        profile = {
            "fake_name": "נשר 42",
            "weighted_tsua": 11.0,
            "weighted_score": 80.0,
            "dominant_risk": "medium",
            "weighted_equity_exposure": 55.0,
            "joined": "10/04/2025",
            "funds": [],
        }
        with patch("src.api.app.get_profile", AsyncMock(return_value=profile)):
            resp = client.get("/community/profile/%D7%A0%D7%A9%D7%A8%2042")
        assert resp.status_code == 200
        assert resp.json()["fake_name"] == "נשר 42"


# ---------------------------------------------------------------------------
# /community/join
# ---------------------------------------------------------------------------


class TestCommunityJoin:
    _PAYLOAD = {
        "client_id": "123456789",
        "funds": [
            {
                "name": "Fund A",
                "id": "103",
                "risk_level": "medium",
                "tsua_1": 18.5,
                "grade": 72.0,
                "amount": 100000.0,
                "pct_of_total": 100.0,
                "equity_exposure": 46.44,
            }
        ],
    }

    def test_returns_200_with_success(self, client):
        mock_result = {
            "success": True,
            "profile": {
                "fake_name": "אריה 55",
                "weighted_tsua": 18.5,
                "weighted_score": 72.0,
                "dominant_risk": "medium",
                "weighted_equity_exposure": 46.4,
                "funds": [],
                "joined": "01/01/2026",
            },
        }
        with patch("src.api.app.join_community", AsyncMock(return_value=mock_result)):
            resp = client.post("/community/join", json=self._PAYLOAD)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
