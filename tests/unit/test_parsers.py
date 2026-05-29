"""Unit tests for the three XML parsers (fund, mislaka, risk_map)."""

import io
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.conftest import MINIMAL_FUNDS_XML, MINIMAL_MISLAKA_XML, MINIMAL_RISKS_MAP_XML, MISLAKA_TWO_TRACKS_XML


# ---------------------------------------------------------------------------
# Risk-map parser
# ---------------------------------------------------------------------------


class TestParseRiskMap:
    def test_parses_equity_rows(self, tmp_path):
        from src.parsers.risk_map_parser import parse_risk_map

        xml_file = tmp_path / "risks.xml"
        xml_file.write_text(MINIMAL_RISKS_MAP_XML, encoding="utf-8")
        result = parse_risk_map(xml_file)
        assert 1001 in result
        assert result[1001] == 10.0
        assert 1002 in result
        assert 1003 in result

    def test_excludes_non_equity_rows(self, tmp_path):
        from src.parsers.risk_map_parser import parse_risk_map

        xml_file = tmp_path / "risks.xml"
        xml_file.write_text(MINIMAL_RISKS_MAP_XML, encoding="utf-8")
        result = parse_risk_map(xml_file)
        # Row for ID 1004 has different SHM_SUG_NECHES and should be excluded
        assert 1004 not in result

    def test_returns_dict_with_int_keys_and_float_values(self, tmp_path):
        from src.parsers.risk_map_parser import parse_risk_map

        xml_file = tmp_path / "risks.xml"
        xml_file.write_text(MINIMAL_RISKS_MAP_XML, encoding="utf-8")
        result = parse_risk_map(xml_file)
        assert all(isinstance(k, int) for k in result)
        assert all(isinstance(v, float) for v in result.values())

    def test_empty_xml_returns_empty_dict(self, tmp_path):
        from src.parsers.risk_map_parser import parse_risk_map

        xml_file = tmp_path / "risks.xml"
        xml_file.write_text("<ROWSET></ROWSET>", encoding="utf-8")
        assert parse_risk_map(xml_file) == {}

    def test_correct_exposure_values(self, tmp_path):
        from src.parsers.risk_map_parser import parse_risk_map

        xml_file = tmp_path / "risks.xml"
        xml_file.write_text(MINIMAL_RISKS_MAP_XML, encoding="utf-8")
        result = parse_risk_map(xml_file)
        assert result[1002] == 50.0
        assert result[1003] == 90.0


# ---------------------------------------------------------------------------
# Fund parser
# ---------------------------------------------------------------------------


class TestParseFundXml:
    @pytest.fixture(autouse=True)
    def patch_risk_classifier(self, monkeypatch):
        import src.core.risk_classifier as rc
        monkeypatch.setattr(rc, "_risks", {
            1001: 10.0,
            1002: 50.0,
            1003: 90.0,
        })

    def test_parses_general_population_funds(self, tmp_path):
        from src.parsers.fund_parser import parse_xml_file

        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, [], remove_special_cases=True)
        ids = [f["ID"] for f in result]
        assert "1001" in ids
        assert "1002" in ids
        assert "1003" in ids

    def test_excludes_non_general_population(self, tmp_path):
        from src.parsers.fund_parser import parse_xml_file

        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, [], remove_special_cases=True)
        ids = [f["ID"] for f in result]
        assert "9999" not in ids

    def test_includes_all_when_remove_special_cases_false(self, tmp_path):
        from src.parsers.fund_parser import parse_xml_file

        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, [], remove_special_cases=False)
        ids = [f["ID"] for f in result]
        assert "9999" in ids

    def test_blacklist_removes_company(self, tmp_path):
        from src.parsers.fund_parser import parse_xml_file

        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, ["Hevra B"], remove_special_cases=True)
        hevrot = [f["hevra"] for f in result]
        assert "Hevra B" not in hevrot

    def test_fund_dict_has_required_keys(self, tmp_path):
        from src.parsers.fund_parser import parse_xml_file

        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, [], remove_special_cases=True)
        required = {
            "ID", "fund_name", "hevra", "SUG", "risk_level",
            "tsua_mitztaberet_letkufa", "tsua_3", "tsua_5",
            "sharp_ribit_hasarot_sikun", "equity_exposure",
        }
        for fund in result:
            assert required.issubset(set(fund.keys()))

    def test_risk_level_assigned_correctly(self, tmp_path):
        from src.parsers.fund_parser import parse_xml_file

        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, [], remove_special_cases=True)
        by_id = {f["ID"]: f for f in result}
        assert by_id["1001"]["risk_level"] == "low"   # 10.0 ≤ 25
        assert by_id["1002"]["risk_level"] == "medium" # 50.0 ≤ 75
        assert by_id["1003"]["risk_level"] == "high"   # 90.0 > 75

    def test_performance_values_parsed_as_floats(self, tmp_path):
        from src.parsers.fund_parser import parse_xml_file

        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, [], remove_special_cases=True)
        fund = next(f for f in result if f["ID"] == "1001")
        assert isinstance(fund["tsua_mitztaberet_letkufa"], float)
        assert isinstance(fund["tsua_3"], float)
        assert isinstance(fund["tsua_5"], float)

    def test_names_stripped_of_whitespace(self, tmp_path):
        from src.parsers.fund_parser import parse_xml_file

        xml_with_spaces = MINIMAL_FUNDS_XML.replace("<SHM_KUPA>Fund Alpha</SHM_KUPA>", "<SHM_KUPA>  Fund Alpha  </SHM_KUPA>")
        xml_file = tmp_path / "funds.xml"
        xml_file.write_text(xml_with_spaces, encoding="utf-8")
        result = parse_xml_file(xml_file, 25, 75, [], remove_special_cases=True)
        fund = next(f for f in result if f["ID"] == "1001")
        assert fund["fund_name"] == "Fund Alpha"


class TestRemoveBadHevrot:
    def test_removes_specified_companies(self):
        from src.parsers.fund_parser import remove_bad_hevrot
        from tests.conftest import make_fund

        funds = [
            make_fund("1", hevra="Good Co"),
            make_fund("2", hevra="Bad Co"),
            make_fund("3", hevra="Also Bad"),
        ]
        result = remove_bad_hevrot(funds, ["Bad Co", "Also Bad"])
        assert len(result) == 1
        assert result[0]["hevra"] == "Good Co"

    def test_empty_blacklist_returns_all(self):
        from src.parsers.fund_parser import remove_bad_hevrot
        from tests.conftest import make_fund

        funds = [make_fund(str(i)) for i in range(3)]
        assert remove_bad_hevrot(funds, []) == funds

    def test_empty_funds_returns_empty(self):
        from src.parsers.fund_parser import remove_bad_hevrot

        assert remove_bad_hevrot([], ["Bad Co"]) == []


# ---------------------------------------------------------------------------
# Mislaka parser
# ---------------------------------------------------------------------------


class TestParseMislakaFile:
    def test_parses_basic_record(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        assert len(result) == 1
        record = result[0]
        assert record["GEMELNET_ID"] == "1001"
        assert record["TOTAL-CHISACHON-MTZBR"] == 200000.0
        assert record["SHEUR-DMEI-NIHUL-TZVIRA"] == pytest.approx(0.75)

    def test_extracts_client_id(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        assert result[0]["MISPAR-ZIHUY-LAKOACH"] == "987654321"

    def test_extracts_seniority_date(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        assert result[0]["TAARICH-HITZTARFUT-MUTZAR"] == "15/03/2019"

    def test_extracts_plan_name(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        assert result[0]["SHEM-TOCHNIT"] == "My Test Plan"

    def test_two_tracks_produces_two_records(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        result = parse_mislaka_file(MISLAKA_TWO_TRACKS_XML)
        assert len(result) == 2

    def test_two_tracks_gemelnet_ids(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        result = parse_mislaka_file(MISLAKA_TWO_TRACKS_XML)
        ids = {r["GEMELNET_ID"] for r in result}
        assert "1001" in ids
        assert "1002" in ids

    def test_two_tracks_balances(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        result = parse_mislaka_file(MISLAKA_TWO_TRACKS_XML)
        balances = sorted(r["TOTAL-CHISACHON-MTZBR"] for r in result)
        assert balances == [50000.0, 80000.0]

    def test_skips_zero_balance_tracks(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        xml = MINIMAL_MISLAKA_XML.replace("<SCHUM-TZVIRA-BAMASLUL>200000.0</SCHUM-TZVIRA-BAMASLUL>",
                                           "<SCHUM-TZVIRA-BAMASLUL>0.0</SCHUM-TZVIRA-BAMASLUL>")
        result = parse_mislaka_file(xml)
        assert result == []

    def test_strips_xml_declaration(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        xml_with_decl = '<?xml version="1.0" encoding="UTF-8"?>' + MINIMAL_MISLAKA_XML
        result = parse_mislaka_file(xml_with_decl)
        assert len(result) == 1

    def test_accepts_bytes_input(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        result = parse_mislaka_file(MINIMAL_MISLAKA_XML.encode("utf-8"))
        assert len(result) == 1

    def test_gemelnet_id_strips_leading_zeros(self):
        from src.parsers.mislaka_parser import parse_mislaka_file

        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        # "001001" → int → str = "1001"
        assert result[0]["GEMELNET_ID"] == "1001"
        assert not result[0]["GEMELNET_ID"].startswith("0")


class TestParseMultipleMislakaFiles:
    def test_combines_results_from_multiple_files(self):
        from src.parsers.mislaka_parser import parse_multible_mislaka_files

        result = parse_multible_mislaka_files([MINIMAL_MISLAKA_XML, MISLAKA_TWO_TRACKS_XML])
        assert len(result) == 3

    def test_empty_list_returns_empty(self):
        from src.parsers.mislaka_parser import parse_multible_mislaka_files

        assert parse_multible_mislaka_files([]) == []

    def test_single_file(self):
        from src.parsers.mislaka_parser import parse_multible_mislaka_files

        result = parse_multible_mislaka_files([MINIMAL_MISLAKA_XML])
        assert len(result) == 1
