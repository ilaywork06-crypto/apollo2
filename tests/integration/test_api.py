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
        patch("src.community.repository.ProfileRepository.init_schema", AsyncMock()),
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
        with patch("src.api.routers.comparison.run_comparison", return_value=self._MOCK_RESULT):
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
        with patch("src.api.routers.comparison.run_comparison", return_value=self._MOCK_RESULT):
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
        with patch("src.api.routers.comparison.run_comparison", return_value={"funds": []}) as mock_engine:
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
        with patch("src.api.routers.comparison.run_comparison", return_value={"funds": []}) as mock_engine:
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
        with patch("src.api.routers.comparison.run_comparison", return_value={"funds": []}) as mock_engine:
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
        with patch("src.api.routers.comparison.run_comparison", return_value={"funds": []}) as mock_engine:
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


    def test_new_params_passed_through(self, client):
        with patch("src.api.routers.comparison.run_comparison", return_value={"funds": []}) as mock_engine:
            client.post(
                "/compare",
                data={
                    "weight_1": "10",
                    "weight_3": "20",
                    "weight_5": "25",
                    "weight_sharp": "35",
                    "weight_liquidity": "10",
                    "low_exposure_threshold": "25",
                    "medium_exposure_threshold": "75",
                    "israel_share_min": "60",
                    "israel_share_max": "100",
                },
                files=[("mislaka_file", ("test.xml", self._MISLAKA_XML.encode(), "text/xml"))],
            )
        _, kwargs = mock_engine.call_args
        assert kwargs["weight_liquidity"] == 10
        assert kwargs["israel_share_min"] == 60
        assert kwargs["israel_share_max"] == 100

    def test_liquidity_weight_defaults_to_zero_for_old_clients(self, client):
        with patch("src.api.routers.comparison.run_comparison", return_value={"funds": []}) as mock_engine:
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
        assert kwargs["weight_liquidity"] == 0
        assert (kwargs["israel_share_min"], kwargs["israel_share_max"]) == (0, 100)


# ---------------------------------------------------------------------------
# /compare/bulk
# ---------------------------------------------------------------------------


class TestCompareBulk:
    _FIELDS = {
        "weight_1": "10",
        "weight_3": "20",
        "weight_5": "25",
        "weight_sharp": "35",
        "weight_liquidity": "10",
        "low_exposure_threshold": "25",
        "medium_exposure_threshold": "75",
    }
    _RESULT = {"clients": [], "errors": [], "skipped": [], "files_received": 0}

    def test_passes_files_and_params(self, client):
        with patch("src.api.routers.comparison.run_bulk_comparison", return_value=self._RESULT) as mock_engine:
            resp = client.post(
                "/compare/bulk",
                data={**self._FIELDS, "bad_hevrot": ["א", "ב"], "override_risk_level": "high"},
                files=[
                    ("mislaka_file", ("a.xml", b"<a/>", "text/xml")),
                    ("mislaka_file", ("b.xml", b"<b/>", "text/xml")),
                ],
            )
        assert resp.status_code == 200
        args, kwargs = mock_engine.call_args
        assert args[0] == [("a.xml", b"<a/>"), ("b.xml", b"<b/>")]
        assert kwargs["weight_liquidity"] == 10
        assert kwargs["bad_hevrot"] == ["א", "ב"]
        assert kwargs["override_risk_level"] == "high"

    def test_accepts_more_than_1000_files(self, client):
        files = [("mislaka_file", (f"f{i}.xml", b"<x/>", "text/xml")) for i in range(1200)]
        with patch("src.api.routers.comparison.run_bulk_comparison", return_value=self._RESULT) as mock_engine:
            resp = client.post("/compare/bulk", data=self._FIELDS, files=files)
        assert resp.status_code == 200
        assert len(mock_engine.call_args[0][0]) == 1200

    def test_missing_files_returns_422(self, client):
        resp = client.post("/compare/bulk", data=self._FIELDS)
        assert resp.status_code == 422

    def test_invalid_weight_returns_422(self, client):
        resp = client.post(
            "/compare/bulk",
            data={**self._FIELDS, "weight_1": "abc"},
            files=[("mislaka_file", ("a.xml", b"<a/>", "text/xml"))],
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /community/leaderboard
# ---------------------------------------------------------------------------


class TestCommunityLeaderboard:
    def test_returns_200(self, client):
        with patch("src.api.routers.community.get_leaderboard", AsyncMock(return_value={"profiles": []})):
            resp = client.get("/community/leaderboard")
        assert resp.status_code == 200

    def test_returns_profiles_key(self, client):
        with patch("src.api.routers.community.get_leaderboard", AsyncMock(return_value={"profiles": []})):
            resp = client.get("/community/leaderboard")
        assert "profiles" in resp.json()


# ---------------------------------------------------------------------------
# /community/profile/{fake_name}
# ---------------------------------------------------------------------------


class TestCommunityProfile:
    def test_returns_404_for_unknown_profile(self, client):
        with patch("src.api.routers.community.get_profile", AsyncMock(return_value=None)):
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
        with patch("src.api.routers.community.get_profile", AsyncMock(return_value=profile)):
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
        with patch("src.api.routers.community.join_community", AsyncMock(return_value=mock_result)):
            resp = client.post("/community/join", json=self._PAYLOAD)
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ---------------------------------------------------------------------------
# End to end over HTTP, with the real engine and data
# ---------------------------------------------------------------------------

from src.comparison.config import GEMEL_NET_PATH, RISKS_MAP_PATH  # noqa: E402
from src.comparison.service import run_comparison  # noqa: E402

needs_data = pytest.mark.skipif(
    not GEMEL_NET_PATH.exists() or not RISKS_MAP_PATH.exists(), reason="Real data files not present"
)

_FORM = {
    "weight_1": "10", "weight_3": "20", "weight_5": "25", "weight_sharp": "35", "weight_liquidity": "10",
    "low_exposure_threshold": "25", "medium_exposure_threshold": "75",
}


def _mislaka_xml(client_id, fund_code, balance="150000.0"):
    return TestCompare._MISLAKA_XML.replace("987654321", client_id).replace("XX000103", fund_code).replace(
        "150000.0", balance
    )


@needs_data
class TestEndToEnd:
    def test_compare_returns_what_the_service_computes(self, client):
        xml = _mislaka_xml("987654321", "XX000103")
        resp = client.post(
            "/compare",
            data={**_FORM, "bad_hevrot": ["אקטיון בע\"מ"]},
            files=[("mislaka_file", ("a.xml", xml.encode("utf-8-sig"), "text/xml"))],
        )
        assert resp.status_code == 200
        expected = run_comparison(
            mislaka_file=[xml], weight_1=10, weight_3=20, weight_5=25, weight_sharp=35, weight_liquidity=10,
            low_exposure_threshold=25, medium_exposure_threshold=75, bad_hevrot=['אקטיון בע"מ'],
        )
        assert resp.json() == json.loads(json.dumps(expected))

    def test_compare_response_shape(self, client):
        resp = client.post(
            "/compare", data=_FORM,
            files=[("mislaka_file", ("a.xml", _mislaka_xml("1", "XX000103").encode(), "text/xml"))],
        )
        body = resp.json()
        holding = body["funds"][0]
        assert holding["client"]["id"] == "103"
        assert {"gross", "israel_equity_share", "liquidity_score", "has_grade"} <= set(holding["alternatives"][0])
        assert set(body["portfolio"]["upside"]) == {"net", "gross"}

    def test_bulk_ranks_real_clients_and_reports_bad_files(self, client):
        files = [
            ("mislaka_file", ("c1.xml", _mislaka_xml("111", "XX000103").encode(), "text/xml")),
            ("mislaka_file", ("c2.xml", _mislaka_xml("222", "XX000127", "300000.0").encode(), "text/xml")),
            ("mislaka_file", ("bad.xml", b"<oops", "text/xml")),
        ]
        body = client.post("/compare/bulk", data=_FORM, files=files).json()
        assert {c["client_id"] for c in body["clients"]} == {"111", "222"}
        upsides = [c["portfolio"]["upside"]["net"]["1"] for c in body["clients"]]
        assert upsides == sorted(upsides, reverse=True)
        assert [e["file"] for e in body["errors"]] == ["bad.xml"]
        assert body["files_received"] == 3


class TestBulkErrors:
    def test_missing_files_explains_why(self, client):
        resp = client.post("/compare/bulk", data=_FORM)
        assert resp.status_code == 422
        assert resp.json()["detail"] == "No mislaka_file uploaded"

    def test_invalid_field_is_named_in_the_error(self, client):
        resp = client.post(
            "/compare/bulk", data={**_FORM, "weight_3": "lots"},
            files=[("mislaka_file", ("a.xml", b"<a/>", "text/xml"))],
        )
        assert resp.status_code == 422
        assert [e["loc"] for e in resp.json()["detail"]] == [["weight_3"]]

    def test_missing_required_field(self, client):
        form = {k: v for k, v in _FORM.items() if k != "weight_sharp"}
        resp = client.post("/compare/bulk", data=form, files=[("mislaka_file", ("a.xml", b"<a/>", "text/xml"))])
        assert resp.status_code == 422
        assert [e["loc"] for e in resp.json()["detail"]] == [["weight_sharp"]]

    def test_defaults_for_optional_fields(self, client):
        form = {k: v for k, v in _FORM.items() if k != "weight_liquidity"}
        with patch("src.api.routers.comparison.run_bulk_comparison", return_value={"clients": []}) as engine:
            client.post("/compare/bulk", data=form, files=[("mislaka_file", ("a.xml", b"<a/>", "text/xml"))])
        kwargs = engine.call_args.kwargs
        assert (kwargs["weight_liquidity"], kwargs["israel_share_min"], kwargs["israel_share_max"]) == (0, 0.0, 100.0)
        assert (kwargs["bad_hevrot"], kwargs["override_risk_level"]) == ([], None)

    def test_uploaded_bytes_are_passed_untouched(self, client):
        raw = '<?xml version="1.0" encoding="windows-1255"?><x>שלום</x>'.encode("cp1255")
        with patch("src.api.routers.comparison.run_bulk_comparison", return_value={"clients": []}) as engine:
            client.post("/compare/bulk", data=_FORM, files=[("mislaka_file", ("h.xml", raw, "text/xml"))])
        assert engine.call_args.args[0] == [("h.xml", raw)]
