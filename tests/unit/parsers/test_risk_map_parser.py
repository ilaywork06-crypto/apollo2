"""Unit tests for src/parsers/risk_map_parser.py"""

from tests.conftest import MINIMAL_RISKS_MAP_XML


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


_EXPOSURES_XML = """\
<ROWSET>
  <Row>
    <ID_KUPA>15311</ID_KUPA>
    <ID_SUG_NECHES>4751</ID_SUG_NECHES>
    <SHM_SUG_NECHES>, חשיפה למניות</SHM_SUG_NECHES>
    <ACHUZ_SUG_NECHES>99.87</ACHUZ_SUG_NECHES>
  </Row>
  <Row>
    <ID_KUPA>15311</ID_KUPA>
    <ID_SUG_NECHES>4752</ID_SUG_NECHES>
    <SHM_SUG_NECHES>חשיפה לחו"ל</SHM_SUG_NECHES>
    <ACHUZ_SUG_NECHES>0.0</ACHUZ_SUG_NECHES>
  </Row>
  <Row>
    <ID_KUPA>127</ID_KUPA>
    <ID_SUG_NECHES>4752</ID_SUG_NECHES>
    <SHM_SUG_NECHES>חשיפה לחו"ל</SHM_SUG_NECHES>
    <ACHUZ_SUG_NECHES>68.9</ACHUZ_SUG_NECHES>
  </Row>
  <Row>
    <ID_KUPA>127</ID_KUPA>
    <ID_SUG_NECHES>4761</ID_SUG_NECHES>
    <SHM_SUG_NECHES>חשיפה למט"ח</SHM_SUG_NECHES>
    <ACHUZ_SUG_NECHES>30.0</ACHUZ_SUG_NECHES>
  </Row>
</ROWSET>
"""


class TestParseExposureMaps:
    def test_returns_equity_and_foreign_maps(self, tmp_path):
        from src.parsers.risk_map_parser import parse_exposure_maps

        xml_file = tmp_path / "risks.xml"
        xml_file.write_text(_EXPOSURES_XML, encoding="utf-8")
        equity, foreign = parse_exposure_maps(xml_file)
        assert equity == {15311: 99.87}
        assert foreign == {15311: 0.0, 127: 68.9}

    def test_currency_exposure_is_not_foreign_exposure(self, tmp_path):
        from src.parsers.risk_map_parser import parse_exposure_maps

        xml_file = tmp_path / "risks.xml"
        xml_file.write_text(_EXPOSURES_XML, encoding="utf-8")
        _, foreign = parse_exposure_maps(xml_file)
        assert foreign[127] == 68.9
