"""Unit tests for src/parsers/fund_parser.py"""

import pytest

from src.comparison.risk_classifier import RiskClassifier
from src.parsers.fund_parser import parse_xml_file
from tests.conftest import MINIMAL_FUNDS_XML


@pytest.fixture
def risk_classifier():
    return RiskClassifier(risks={
        1001: 10.0,
        1002: 50.0,
        1003: 90.0,
    })


class TestParseFundXml:
    def test_parses_general_population_funds(self, tmp_path, risk_classifier):
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, risk_classifier, remove_special_cases=True)
        ids = [f["ID"] for f in result]
        assert "1001" in ids
        assert "1002" in ids
        assert "1003" in ids

    def test_excludes_non_general_population(self, tmp_path, risk_classifier):
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, risk_classifier, remove_special_cases=True)
        ids = [f["ID"] for f in result]
        assert "9999" not in ids

    def test_includes_all_when_remove_special_cases_false(self, tmp_path, risk_classifier):
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, risk_classifier, remove_special_cases=False)
        ids = [f["ID"] for f in result]
        assert "9999" in ids

    def test_fund_dict_has_required_keys(self, tmp_path, risk_classifier):
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, risk_classifier, remove_special_cases=True)
        required = {
            "ID", "fund_name", "hevra", "SUG", "risk_level",
            "tsua_mitztaberet_letkufa", "tsua_3", "tsua_5",
            "sharp_ribit_hasarot_sikun", "equity_exposure",
        }
        for fund in result:
            assert required.issubset(set(fund.keys()))

    def test_risk_level_assigned_correctly(self, tmp_path, risk_classifier):
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, risk_classifier, remove_special_cases=True)
        by_id = {f["ID"]: f for f in result}
        assert by_id["1001"]["risk_level"] == "low"     # 10.0 <= 25
        assert by_id["1002"]["risk_level"] == "medium"  # 50.0 <= 75
        assert by_id["1003"]["risk_level"] == "high"    # 90.0 > 75

    def test_performance_values_parsed_as_floats(self, tmp_path, risk_classifier):
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, risk_classifier, remove_special_cases=True)
        fund = next(f for f in result if f["ID"] == "1001")
        assert isinstance(fund["tsua_mitztaberet_letkufa"], float)
        assert isinstance(fund["tsua_3"], float)
        assert isinstance(fund["tsua_5"], float)

    def test_names_stripped_of_whitespace(self, tmp_path, risk_classifier):
        xml_with_spaces = MINIMAL_FUNDS_XML.replace("<SHM_KUPA>Fund Alpha</SHM_KUPA>", "<SHM_KUPA>  Fund Alpha  </SHM_KUPA>")
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(xml_with_spaces, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, risk_classifier, remove_special_cases=True)
        fund = next(f for f in result if f["ID"] == "1001")
        assert fund["fund_name"] == "Fund Alpha"
