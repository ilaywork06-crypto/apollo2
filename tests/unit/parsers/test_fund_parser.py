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


_LIQUIDITY_FUNDS_XML = """\
<ROWSET>
  <Row>
    <UCHLUSIYAT_YAAD>כלל האוכלוסיה</UCHLUSIYAT_YAAD>
    <SUG_KUPA>תגמולים ואישית לפיצויים</SUG_KUPA>
    <ID>1001</ID>
    <SHM_KUPA>Inflow Fund</SHM_KUPA>
    <SHM_HEVRA_MENAHELET>Hevra A</SHM_HEVRA_MENAHELET>
    <TZVIRA_NETO>4657.31</TZVIRA_NETO>
    <YITRAT_NCHASIM_LSOF_TKUFA>24824.09</YITRAT_NCHASIM_LSOF_TKUFA>
  </Row>
  <Row>
    <UCHLUSIYAT_YAAD>כלל האוכלוסיה</UCHLUSIYAT_YAAD>
    <SUG_KUPA>תגמולים ואישית לפיצויים</SUG_KUPA>
    <ID>1002</ID>
    <SHM_KUPA>Outflow Fund</SHM_KUPA>
    <SHM_HEVRA_MENAHELET>Hevra B</SHM_HEVRA_MENAHELET>
    <TZVIRA_NETO>-50.0</TZVIRA_NETO>
    <YITRAT_NCHASIM_LSOF_TKUFA>200.0</YITRAT_NCHASIM_LSOF_TKUFA>
  </Row>
  <Row>
    <UCHLUSIYAT_YAAD>כלל האוכלוסיה</UCHLUSIYAT_YAAD>
    <SUG_KUPA>תגמולים ואישית לפיצויים</SUG_KUPA>
    <ID>1003</ID>
    <SHM_KUPA>Empty Fund</SHM_KUPA>
    <SHM_HEVRA_MENAHELET>Hevra C</SHM_HEVRA_MENAHELET>
    <TZVIRA_NETO>-3.0</TZVIRA_NETO>
    <YITRAT_NCHASIM_LSOF_TKUFA>0.0</YITRAT_NCHASIM_LSOF_TKUFA>
  </Row>
</ROWSET>
"""


class TestLiquidityAndGeography:
    def _parse(self, tmp_path):
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(_LIQUIDITY_FUNDS_XML, encoding="utf-8")
        rc = RiskClassifier(risks={1001: 99.87, 1002: 60.0}, foreign={1001: 0.0, 1002: 45.0})
        return {f["ID"]: f for f in parse_xml_file(xml_file, 25, 75, rc, remove_special_cases=True)}

    def test_liquidity_index_is_net_accumulation_over_assets(self, tmp_path):
        funds = self._parse(tmp_path)
        assert funds["1001"]["net_accumulation"] == 4657.31
        assert funds["1001"]["total_assets"] == 24824.09
        assert funds["1001"]["liquidity_index"] == pytest.approx(4657.31 / 24824.09 * 100)

    def test_outflows_give_negative_liquidity(self, tmp_path):
        assert self._parse(tmp_path)["1002"]["liquidity_index"] == pytest.approx(-25.0)

    def test_no_assets_means_no_liquidity_index(self, tmp_path):
        assert self._parse(tmp_path)["1003"]["liquidity_index"] is None

    def test_equity_geography_fields(self, tmp_path):
        funds = self._parse(tmp_path)
        assert funds["1001"]["foreign_exposure"] == 0.0
        assert funds["1001"]["israel_equity_exposure"] == 99.87
        assert funds["1001"]["israel_equity_share"] == 100.0
        assert funds["1002"]["israel_equity_exposure"] == 15.0
        assert funds["1002"]["israel_equity_share"] == 25.0
        assert funds["1003"]["israel_equity_share"] is None


class TestEveryField:
    def test_first_fixture_row_in_full(self, tmp_path):
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML.replace(
            "<HITMAHUT_RASHIT>N/A</HITMAHUT_RASHIT>", "<HITMAHUT_RASHIT> מדרגות </HITMAHUT_RASHIT>", 1
        ).replace(
            "<HITMAHUT_MISHNIT>N/A</HITMAHUT_MISHNIT>", "<HITMAHUT_MISHNIT>50-60</HITMAHUT_MISHNIT>", 1
        ), encoding="utf-8")
        rc = RiskClassifier(risks={1001: 40.0}, foreign={1001: 10.0})
        fund = parse_xml_file(xml_file, 25, 75, rc, remove_special_cases=True)[0]
        assert fund == {
            "UCHLUSIYAT_YAAD": "כלל האוכלוסיה",
            "SUG": "תגמולים ואישית לפיצויים",
            "ID": "1001",
            "tsua_mitztaberet_letkufa": 15.0,
            "sharp_ribit_hasarot_sikun": 1.8,
            "fund_name": "Fund Alpha",
            "hevra": "Hevra A",
            "hitmahut_rashit": "מדרגות",
            "hitmahut_mishnit": "50-60",
            "tsua_3": 10.0,
            "tsua_5": 9.0,
            "num_hevra": "1",
            "risk_level": "medium",
            "equity_exposure": 40.0,
            "foreign_exposure": 10.0,
            "israel_equity_exposure": 30.0,
            "israel_equity_share": 75.0,
            "net_accumulation": 0.0,
            "total_assets": 0.0,
            "liquidity_index": None,
        }


class TestCalculateLiquidityIndex:
    def test_ratio_in_percent(self):
        from src.parsers.fund_parser import calculate_liquidity_index

        assert calculate_liquidity_index(25.0, 200.0) == 12.5

    def test_assets_below_one_million_still_count(self):
        # GemeNet reports millions of NIS; a fund with half a million is small, not empty
        from src.parsers.fund_parser import calculate_liquidity_index

        assert calculate_liquidity_index(1.0, 0.5) == 200.0

    @pytest.mark.parametrize("assets", [0.0, -3.0])
    def test_no_positive_assets(self, assets):
        from src.parsers.fund_parser import calculate_liquidity_index

        assert calculate_liquidity_index(5.0, assets) is None
