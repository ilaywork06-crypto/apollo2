"""Unit tests for src/comparison/risk_classifier.py"""

import pytest

from src.comparison.risk_classifier import RiskClassifier


@pytest.fixture
def classifier():
    risks = {
        1001: 10.0,   # low  (<= 25)
        1002: 50.0,   # medium (<= 75)
        1003: 90.0,   # high  (> 75)
        1004: 25.0,   # boundary: exactly low threshold
        1005: 75.0,   # boundary: exactly medium threshold
        1006: 0.0,    # zero exposure -> low
        1007: 100.0,  # full equity -> high
    }
    return RiskClassifier(risks=risks)


class TestConstruction:
    def test_requires_risks_or_path(self):
        with pytest.raises(ValueError):
            RiskClassifier()

    def test_risks_dict_used_directly(self):
        rc = RiskClassifier(risks={1: 50.0})
        assert rc.get_equity_exposure(1) == 50.0

    def test_path_loads_from_xml(self, tmp_path):
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
        rc = RiskClassifier(path=xml_path)
        assert rc.get_equity_exposure(5555) == 35.0


class TestGetRiskLevel:
    def test_low_exposure(self, classifier):
        assert classifier.get_risk_level(1001, 25, 75) == "low"

    def test_medium_exposure(self, classifier):
        assert classifier.get_risk_level(1002, 25, 75) == "medium"

    def test_high_exposure(self, classifier):
        assert classifier.get_risk_level(1003, 25, 75) == "high"

    def test_unknown_fund_is_invalid(self, classifier):
        assert classifier.get_risk_level(9999, 25, 75) == "invalid"

    def test_exactly_low_threshold_is_low(self, classifier):
        assert classifier.get_risk_level(1004, 25, 75) == "low"

    def test_exactly_medium_threshold_is_medium(self, classifier):
        assert classifier.get_risk_level(1005, 25, 75) == "medium"

    def test_zero_exposure_is_low(self, classifier):
        assert classifier.get_risk_level(1006, 25, 75) == "low"

    def test_full_exposure_is_high(self, classifier):
        assert classifier.get_risk_level(1007, 25, 75) == "high"

    def test_custom_thresholds_low(self, classifier):
        assert classifier.get_risk_level(1002, 60, 80) == "low"

    def test_custom_thresholds_medium(self, classifier):
        assert classifier.get_risk_level(1003, 25, 95) == "medium"

    def test_custom_thresholds_high(self, classifier):
        assert classifier.get_risk_level(1003, 25, 75) == "high"

    def test_one_below_medium_threshold(self):
        classifier = RiskClassifier(risks={2000: 74.9})
        assert classifier.get_risk_level(2000, 25, 75) == "medium"

    def test_one_above_medium_threshold(self):
        classifier = RiskClassifier(risks={2001: 75.1})
        assert classifier.get_risk_level(2001, 25, 75) == "high"


class TestGetEquityExposure:
    def test_known_fund_returns_float(self, classifier):
        assert classifier.get_equity_exposure(1001) == 10.0

    def test_unknown_fund_returns_none(self, classifier):
        assert classifier.get_equity_exposure(9999) is None

    def test_high_exposure_fund(self, classifier):
        assert classifier.get_equity_exposure(1003) == 90.0

    def test_zero_exposure_fund(self, classifier):
        assert classifier.get_equity_exposure(1006) == 0.0
