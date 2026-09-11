"""Unit tests for src/parsers/mislaka/parser.py"""

import pytest

from src.parsers.mislaka.parser import parse_mislaka_file, parse_multible_mislaka_files
from tests.conftest import (
    MINIMAL_MISLAKA_XML,
    MISLAKA_TWO_TRACKS_XML,
    MISLAKA_UNIFORM_FEE_XML,
)


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

    def test_skips_residual_balance_tracks(self):
        # A one-agora leftover (0.01) is a dead account and must not be shown,
        # even though it is not exactly 0.0.
        xml = MINIMAL_MISLAKA_XML.replace("<SCHUM-TZVIRA-BAMASLUL>200000.0</SCHUM-TZVIRA-BAMASLUL>",
                                           "<SCHUM-TZVIRA-BAMASLUL>0.01</SCHUM-TZVIRA-BAMASLUL>")
        result = parse_mislaka_file(xml)
        assert result == []

    def test_keeps_small_real_balance_tracks(self):
        # A small but real balance (>= 1 NIS) is still a live account.
        xml = MINIMAL_MISLAKA_XML.replace("<SCHUM-TZVIRA-BAMASLUL>200000.0</SCHUM-TZVIRA-BAMASLUL>",
                                           "<SCHUM-TZVIRA-BAMASLUL>38.70</SCHUM-TZVIRA-BAMASLUL>")
        result = parse_mislaka_file(xml)
        assert len(result) == 1
        assert result[0]["TOTAL-CHISACHON-MTZBR"] == pytest.approx(38.70)

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

    def test_recovers_uniform_fee_without_per_track_key(self):
        # Harel-style file: no track-level fee fields and the structure-level
        # fee declares uniform fees (DMEI-NIHUL-ACHIDIM=1) without the per-track
        # key, so the fee must be recovered from the policy-wide fallback.
        result = parse_mislaka_file(MISLAKA_UNIFORM_FEE_XML)
        assert len(result) == 1
        assert result[0]["SHEUR-DMEI-NIHUL-TZVIRA"] == pytest.approx(0.7)
        assert result[0]["SHEUR-DMEI-NIHUL-HAFKADA"] == pytest.approx(0.0)


class TestParseMultipleMislakaFiles:
    def test_combines_results_from_multiple_files(self):
        result = parse_multible_mislaka_files([MINIMAL_MISLAKA_XML, MISLAKA_TWO_TRACKS_XML])
        assert len(result) == 3

    def test_empty_list_returns_empty(self):
        assert parse_multible_mislaka_files([]) == []

    def test_single_file(self):
        result = parse_multible_mislaka_files([MINIMAL_MISLAKA_XML])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Real-world file variations
# ---------------------------------------------------------------------------


def _file(client_block="", mutzar_client_block="", track_extra="", polisa_extra="", code="XX001001",
          balance="200000.0", fee_fields="<SHEUR-DMEI-NIHUL-HISACHON>0.75</SHEUR-DMEI-NIHUL-HISACHON>"):
    return f"""<MislakaRoot>
  {client_block}
  <Mutzar>
    <KOD-MEZAHE-YATZRAN> Yatzran-7 </KOD-MEZAHE-YATZRAN>
    {mutzar_client_block}
    <HeshbonOPolisa>
      <SHEM-TOCHNIT> תוכנית ותיקה </SHEM-TOCHNIT>
      <TAARICH-HITZTARFUT-MUTZAR>20180115</TAARICH-HITZTARFUT-MUTZAR>
      {polisa_extra}
      <PirteiTaktziv>
        <PerutMasluleiHashkaa>
          <SCHUM-TZVIRA-BAMASLUL>{balance}</SCHUM-TZVIRA-BAMASLUL>
          <KOD-MASLUL-HASHKAA>{code}</KOD-MASLUL-HASHKAA>
          {fee_fields}
          {track_extra}
        </PerutMasluleiHashkaa>
      </PirteiTaktziv>
    </HeshbonOPolisa>
  </Mutzar>
</MislakaRoot>"""


def _client(client_id="039485721", first="דנה", last="כהן"):
    parts = [f"<MISPAR-ZIHUY-LAKOACH>{client_id}</MISPAR-ZIHUY-LAKOACH>" if client_id is not None else ""]
    if first is not None:
        parts.append(f"<SHEM-PRATI>{first}</SHEM-PRATI>")
    if last is not None:
        parts.append(f"<SHEM-MISHPACHA>{last}</SHEM-MISHPACHA>")
    return "<YeshutLakoach>" + "".join(parts) + "</YeshutLakoach>"


class TestEncodings:
    def test_windows_1255_text_with_its_declaration(self):
        # /compare decodes uploads to text; the declaration must not make lxml re-decode it
        text = '<?xml version="1.0" encoding="windows-1255"?>\n' + _file(_client())
        record = parse_mislaka_file(text)[0]
        assert record["SHEM-LAKOACH"] == "דנה כהן"
        assert record["SHEM-TOCHNIT"] == "תוכנית ותיקה"

    def test_windows_1255_bytes_are_decoded_by_their_declaration(self):
        raw = ('<?xml version="1.0" encoding="windows-1255"?>\n' + _file(_client())).encode("cp1255")
        assert parse_mislaka_file(raw)[0]["SHEM-LAKOACH"] == "דנה כהן"

    def test_utf8_bytes_with_bom(self):
        raw = "\ufeff".encode("utf-8") + _file(_client()).encode("utf-8")
        assert parse_mislaka_file(raw)[0]["SHEM-LAKOACH"] == "דנה כהן"


class TestClientIdentity:
    def test_file_level_id_and_name(self):
        record = parse_mislaka_file(_file(_client()))[0]
        assert (record["MISPAR-ZIHUY-LAKOACH"], record["SHEM-LAKOACH"]) == ("039485721", "דנה כהן")

    def test_missing_client_block(self):
        record = parse_mislaka_file(_file())[0]
        assert (record["MISPAR-ZIHUY-LAKOACH"], record["SHEM-LAKOACH"]) == ("unknown", "")

    def test_empty_id_element_is_unknown(self):
        record = parse_mislaka_file(_file(_client(client_id="")))[0]
        assert record["MISPAR-ZIHUY-LAKOACH"] == "unknown"

    def test_product_level_client_overrides_the_file_level_one(self):
        record = parse_mislaka_file(_file(_client("111"), mutzar_client_block=_client("222")))[0]
        assert record["MISPAR-ZIHUY-LAKOACH"] == "222"

    def test_product_level_client_without_an_id_keeps_the_file_level_one(self):
        record = parse_mislaka_file(_file(_client("111"), mutzar_client_block=_client(client_id=None)))[0]
        assert record["MISPAR-ZIHUY-LAKOACH"] == "111"

    def test_first_name_only(self):
        assert parse_mislaka_file(_file(_client(last=None)))[0]["SHEM-LAKOACH"] == "דנה"

    def test_last_name_only(self):
        assert parse_mislaka_file(_file(_client(first=None)))[0]["SHEM-LAKOACH"] == "כהן"

    def test_blank_name_parts_are_dropped(self):
        assert parse_mislaka_file(_file(_client(first="  ", last="כהן")))[0]["SHEM-LAKOACH"] == "כהן"


class TestHoldingFields:
    def test_plan_date_and_producer_are_trimmed(self):
        record = parse_mislaka_file(_file(_client()))[0]
        assert record["SHEM-TOCHNIT"] == "תוכנית ותיקה"
        assert record["TAARICH-HITZTARFUT-MUTZAR"] == "20180115"
        assert record["KOD-MEZAHE-YATZRAN"] == "Yatzran-7"

    def test_long_track_code_uses_its_last_six_digits(self):
        record = parse_mislaka_file(_file(code="512267592000000000001540000154"))[0]
        assert record["GEMELNET_ID"] == "154"


_KEYED_FEES = """
      <PerutHotzaot><MivneDmeiNihul>
        <PerutMivneDmeiNihul>
          <SUG-HOTZAA>1</SUG-HOTZAA>
          <KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM>XX001001</KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM>
          <SHEUR-DMEI-NIHUL>0.52</SHEUR-DMEI-NIHUL>
        </PerutMivneDmeiNihul>
        <PerutMivneDmeiNihul>
          <SUG-HOTZAA>2</SUG-HOTZAA>
          <KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM>XX001001</KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM>
          <SHEUR-DMEI-NIHUL>1.9</SHEUR-DMEI-NIHUL>
        </PerutMivneDmeiNihul>
      </MivneDmeiNihul></PerutHotzaot>"""

_UNIFORM_DEPOSIT_FEE = """
      <PerutHotzaot><MivneDmeiNihul>
        <PerutMivneDmeiNihul>
          <SUG-HOTZAA>2</SUG-HOTZAA>
          <SHEUR-DMEI-NIHUL>2.5</SHEUR-DMEI-NIHUL>
          <DMEI-NIHUL-ACHIDIM>1</DMEI-NIHUL-ACHIDIM>
        </PerutMivneDmeiNihul>
      </MivneDmeiNihul></PerutHotzaot>"""


class TestFeeResolution:
    def test_structure_fees_keyed_by_track_code(self):
        record = parse_mislaka_file(_file(polisa_extra=_KEYED_FEES, fee_fields=""))[0]
        assert record["SHEUR-DMEI-NIHUL-TZVIRA"] == pytest.approx(0.52)
        assert record["SHEUR-DMEI-NIHUL-HAFKADA"] == pytest.approx(1.9)

    def test_uniform_deposit_fee(self):
        record = parse_mislaka_file(_file(polisa_extra=_UNIFORM_DEPOSIT_FEE))[0]
        assert record["SHEUR-DMEI-NIHUL-HAFKADA"] == pytest.approx(2.5)

    def test_highest_accumulation_fee_wins(self):
        record = parse_mislaka_file(_file(polisa_extra=_KEYED_FEES))[0]  # track says 0.75, structure 0.52
        assert record["SHEUR-DMEI-NIHUL-TZVIRA"] == pytest.approx(0.75)
