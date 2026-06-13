"""Unit tests for src/parsers/mislaka/parser.py"""

import pytest

from src.parsers.mislaka.parser import parse_mislaka_file, parse_multible_mislaka_files
from tests.conftest import MINIMAL_MISLAKA_XML, MISLAKA_TWO_TRACKS_XML


class TestParseMislakaFile:
    def test_parses_basic_record(self):
        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        assert len(result) == 1
        record = result[0]
        assert record["GEMELNET_ID"] == "1001"
        assert record["TOTAL-CHISACHON-MTZBR"] == 200000.0
        assert record["SHEUR-DMEI-NIHUL-TZVIRA"] == pytest.approx(0.75)

    def test_extracts_client_id(self):
        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        assert result[0]["MISPAR-ZIHUY-LAKOACH"] == "987654321"

    def test_extracts_seniority_date(self):
        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        assert result[0]["TAARICH-HITZTARFUT-MUTZAR"] == "15/03/2019"

    def test_extracts_plan_name(self):
        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        assert result[0]["SHEM-TOCHNIT"] == "My Test Plan"

    def test_two_tracks_produces_two_records(self):
        result = parse_mislaka_file(MISLAKA_TWO_TRACKS_XML)
        assert len(result) == 2

    def test_two_tracks_gemelnet_ids(self):
        result = parse_mislaka_file(MISLAKA_TWO_TRACKS_XML)
        ids = {r["GEMELNET_ID"] for r in result}
        assert "1001" in ids
        assert "1002" in ids

    def test_two_tracks_balances(self):
        result = parse_mislaka_file(MISLAKA_TWO_TRACKS_XML)
        balances = sorted(r["TOTAL-CHISACHON-MTZBR"] for r in result)
        assert balances == [50000.0, 80000.0]

    def test_skips_zero_balance_tracks(self):
        xml = MINIMAL_MISLAKA_XML.replace("<SCHUM-TZVIRA-BAMASLUL>200000.0</SCHUM-TZVIRA-BAMASLUL>",
                                           "<SCHUM-TZVIRA-BAMASLUL>0.0</SCHUM-TZVIRA-BAMASLUL>")
        result = parse_mislaka_file(xml)
        assert result == []

    def test_strips_xml_declaration(self):
        xml_with_decl = '<?xml version="1.0" encoding="UTF-8"?>' + MINIMAL_MISLAKA_XML
        result = parse_mislaka_file(xml_with_decl)
        assert len(result) == 1

    def test_accepts_bytes_input(self):
        result = parse_mislaka_file(MINIMAL_MISLAKA_XML.encode("utf-8"))
        assert len(result) == 1

    def test_gemelnet_id_strips_leading_zeros(self):
        result = parse_mislaka_file(MINIMAL_MISLAKA_XML)
        # "001001" -> int -> str = "1001"
        assert result[0]["GEMELNET_ID"] == "1001"
        assert not result[0]["GEMELNET_ID"].startswith("0")


class TestParseMultipleMislakaFiles:
    def test_combines_results_from_multiple_files(self):
        result = parse_multible_mislaka_files([MINIMAL_MISLAKA_XML, MISLAKA_TWO_TRACKS_XML])
        assert len(result) == 3

    def test_empty_list_returns_empty(self):
        assert parse_multible_mislaka_files([]) == []

    def test_single_file(self):
        result = parse_multible_mislaka_files([MINIMAL_MISLAKA_XML])
        assert len(result) == 1
