"""Unit tests for src/parsers/mislaka/fee_resolver.py"""

import lxml.etree as ET

from src.parsers.mislaka.fee_resolver import map_dmey_nihul, resolve_uniform_dmey_nihul


FEE_STRUCTURE_XML = """\
<MislakaRoot>
  <PerutMivneDmeiNihul>
    <SUG-HOTZAA>1</SUG-HOTZAA>
    <KOD-MASLUL-DMEI-NIHUL>XX001001</KOD-MASLUL-DMEI-NIHUL>
    <KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM>YY001001</KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM>
    <SHEUR-DMEI-NIHUL>0.6</SHEUR-DMEI-NIHUL>
  </PerutMivneDmeiNihul>
  <PerutMivneDmeiNihul>
    <SUG-HOTZAA>2</SUG-HOTZAA>
    <KOD-MASLUL-DMEI-NIHUL>XX001002</KOD-MASLUL-DMEI-NIHUL>
    <KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM>YY001002</KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM>
    <SHEUR-DMEI-NIHUL>0.3</SHEUR-DMEI-NIHUL>
  </PerutMivneDmeiNihul>
</MislakaRoot>
"""


class TestMapDmeyNihul:
    def test_filters_by_sug_hotzaa(self):
        root = ET.fromstring(FEE_STRUCTURE_XML.encode("utf-8"))
        tzvira = map_dmey_nihul(root, 1)
        assert tzvira["XX001001"] == 0.6
        assert "XX001002" not in tzvira

    def test_maps_both_track_code_keys(self):
        root = ET.fromstring(FEE_STRUCTURE_XML.encode("utf-8"))
        tzvira = map_dmey_nihul(root, 1)
        assert tzvira["XX001001"] == 0.6
        assert tzvira["YY001001"] == 0.6

    def test_sug_2_returns_deposit_fees(self):
        root = ET.fromstring(FEE_STRUCTURE_XML.encode("utf-8"))
        hafkada = map_dmey_nihul(root, 2)
        assert hafkada["XX001002"] == 0.3
        assert hafkada["YY001002"] == 0.3

    def test_no_matching_sug_returns_empty(self):
        root = ET.fromstring(FEE_STRUCTURE_XML.encode("utf-8"))
        assert map_dmey_nihul(root, 99) == {}

    def test_empty_root_returns_empty(self):
        root = ET.fromstring(b"<MislakaRoot></MislakaRoot>")
        assert map_dmey_nihul(root, 1) == {}


# Harel-style policy: uniform fees declared (DMEI-NIHUL-ACHIDIM=1) with no
# per-track KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM key.
UNIFORM_FEE_POLISA_XML = """\
<HeshbonOPolisa>
  <PerutHotzaot>
    <MivneDmeiNihul>
      <PerutMivneDmeiNihul>
        <SUG-HOTZAA>1</SUG-HOTZAA>
        <SHEUR-DMEI-NIHUL>0.7</SHEUR-DMEI-NIHUL>
        <DMEI-NIHUL-ACHIDIM>1</DMEI-NIHUL-ACHIDIM>
      </PerutMivneDmeiNihul>
      <PerutMivneDmeiNihul>
        <SUG-HOTZAA>2</SUG-HOTZAA>
        <SHEUR-DMEI-NIHUL>0.0</SHEUR-DMEI-NIHUL>
        <DMEI-NIHUL-ACHIDIM>1</DMEI-NIHUL-ACHIDIM>
      </PerutMivneDmeiNihul>
    </MivneDmeiNihul>
  </PerutHotzaot>
</HeshbonOPolisa>
"""

# Non-uniform policy: fees differ per track (DMEI-NIHUL-ACHIDIM=2), so the
# uniform fallback must NOT apply.
NON_UNIFORM_FEE_POLISA_XML = """\
<HeshbonOPolisa>
  <PerutHotzaot>
    <MivneDmeiNihul>
      <PerutMivneDmeiNihul>
        <SUG-HOTZAA>1</SUG-HOTZAA>
        <SHEUR-DMEI-NIHUL>0.7</SHEUR-DMEI-NIHUL>
        <DMEI-NIHUL-ACHIDIM>2</DMEI-NIHUL-ACHIDIM>
      </PerutMivneDmeiNihul>
    </MivneDmeiNihul>
  </PerutHotzaot>
</HeshbonOPolisa>
"""


class TestResolveUniformDmeyNihul:
    def test_returns_uniform_accumulation_fee(self):
        polisa = ET.fromstring(UNIFORM_FEE_POLISA_XML.encode("utf-8"))
        assert resolve_uniform_dmey_nihul(polisa, 1) == 0.7

    def test_returns_uniform_deposit_fee(self):
        polisa = ET.fromstring(UNIFORM_FEE_POLISA_XML.encode("utf-8"))
        assert resolve_uniform_dmey_nihul(polisa, 2) == 0.0

    def test_ignores_non_uniform_fees(self):
        # DMEI-NIHUL-ACHIDIM=2 means fees genuinely differ per track, so no
        # policy-wide fallback should be produced.
        polisa = ET.fromstring(NON_UNIFORM_FEE_POLISA_XML.encode("utf-8"))
        assert resolve_uniform_dmey_nihul(polisa, 1) == 0.0

    def test_no_fee_structure_returns_zero(self):
        polisa = ET.fromstring(b"<HeshbonOPolisa></HeshbonOPolisa>")
        assert resolve_uniform_dmey_nihul(polisa, 1) == 0.0
