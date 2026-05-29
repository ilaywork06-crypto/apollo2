"""Unit tests for src/core/risk_classifier.py"""

import pytest

import src.core.risk_classifier as rc


@pytest.fixture(autouse=True)
def patch_risks(monkeypatch):
    """Replace the module-level cache with a controlled test dict."""
    test_risks = {
        1001: 10.0,   # low  (≤ 25)
        1002: 50.0,   # medium (≤ 75)
        1003: 90.0,   # high  (> 75)
        1004: 25.0,   # boundary: exactly low threshold
        1005: 75.0,   # boundary: exactly medium threshold
        1006: 0.0,    # zero exposure → low
        1007: 100.0,  # full equity → high
    }
    monkeypatch.setattr(rc, "_risks", test_risks)


class TestGetRiskLevel:
    def test_low_exposure(self):
        assert rc.get_risk_level(1001, 25, 75) == "low"

    def test_medium_exposure(self):
        assert rc.get_risk_level(1002, 25, 75) == "medium"

    def test_high_exposure(self):
        assert rc.get_risk_level(1003, 25, 75) == "high"

    def test_unknown_fund_is_invalid(self):
        assert rc.get_risk_level(9999, 25, 75) == "invalid"

    def test_exactly_low_threshold_is_low(self):
        assert rc.get_risk_level(1004, 25, 75) == "low"

    def test_exactly_medium_threshold_is_medium(self):
        assert rc.get_risk_level(1005, 25, 75) == "medium"

    def test_zero_exposure_is_low(self):
        assert rc.get_risk_level(1006, 25, 75) == "low"

    def test_full_exposure_is_high(self):
        assert rc.get_risk_level(1007, 25, 75) == "high"

    def test_custom_thresholds_low(self):
        assert rc.get_risk_level(1002, 60, 80) == "low"

    def test_custom_thresholds_medium(self):
        assert rc.get_risk_level(1003, 25, 95) == "medium"

    def test_custom_thresholds_high(self):
        assert rc.get_risk_level(1003, 25, 75) == "high"

    def test_one_below_medium_threshold(self):
        rc._risks[2000] = 74.9
        assert rc.get_risk_level(2000, 25, 75) == "medium"

    def test_one_above_medium_threshold(self):
        rc._risks[2001] = 75.1
        assert rc.get_risk_level(2001, 25, 75) == "high"


class TestGetEquityExposure:
    def test_known_fund_returns_float(self):
        assert rc.get_equity_exposure(1001) == 10.0

    def test_unknown_fund_returns_none(self):
        assert rc.get_equity_exposure(9999) is None

    def test_high_exposure_fund(self):
        assert rc.get_equity_exposure(1003) == 90.0

    def test_zero_exposure_fund(self):
        assert rc.get_equity_exposure(1006) == 0.0


class TestLoad:
    def test_load_is_noop_when_risks_already_populated(self, tmp_path):
        """load() should not overwrite an already-populated cache."""
        xml_path = tmp_path / "risks.xml"
        xml_path.write_text("<ROWSET></ROWSET>", encoding="utf-8")
        before = dict(rc._risks)
        rc.load(xml_path)
        assert rc._risks == before

    def test_load_populates_empty_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rc, "_risks", {})
        xml_content = """\
<ROWSET>
  <Row>
    <SHM_SUG_NECHES>, חשיפה למניות</SHM_SUG_NECHES>
    <ID_KUPA>5555</ID_KUPA>
    <ACHUZ_SUG_NECHES>35.0</ACHUZ_SUG_NECHES>
  </Row>
</ROWSET>"""
        xml_path = tmp_path / "risks.xml"
        xml_path.write_text(xml_content, encoding="utf-8")
        rc.load(xml_path)
        assert rc._risks[5555] == 35.0
