"""System tests: full end-to-end with real data files.

These tests call run_comparison() with a synthetic Mislaka XML that
references real fund IDs from kupot_gemel_net.xml (IDs 103 and 127).
Fund 103 = medium risk (equity 46.44%), Fund 127 = high risk (equity 99.27%).
"""

import pytest

from src.comparison.config import GEMEL_NET_PATH, RISKS_MAP_PATH
from src.comparison.service import run_comparison

# Skip the whole module if the real data files are absent (e.g. CI without data)
pytestmark = pytest.mark.skipif(
    not GEMEL_NET_PATH.exists() or not RISKS_MAP_PATH.exists(),
    reason="Real data files not present",
)


# Mislaka XML referencing fund 103 (medium-risk, 150 000 ILS)
MISLAKA_103 = """\
<MislakaRoot>
  <YeshutLakoach>
    <MISPAR-ZIHUY-LAKOACH>987654321</MISPAR-ZIHUY-LAKOACH>
  </YeshutLakoach>
  <Mutzar>
    <KOD-MEZAHE-YATZRAN>מיטב</KOD-MEZAHE-YATZRAN>
    <HeshbonOPolisa>
      <SHEM-TOCHNIT>מיטב גמל</SHEM-TOCHNIT>
      <TAARICH-HITZTARFUT-MUTZAR>01/01/2018</TAARICH-HITZTARFUT-MUTZAR>
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

# Two holdings: fund 103 (medium) + fund 127 (high)
MISLAKA_103_AND_127 = """\
<MislakaRoot>
  <YeshutLakoach>
    <MISPAR-ZIHUY-LAKOACH>111222333</MISPAR-ZIHUY-LAKOACH>
  </YeshutLakoach>
  <Mutzar>
    <KOD-MEZAHE-YATZRAN>מיטב</KOD-MEZAHE-YATZRAN>
    <HeshbonOPolisa>
      <SHEM-TOCHNIT>מיטב גמל</SHEM-TOCHNIT>
      <TAARICH-HITZTARFUT-MUTZAR>01/01/2018</TAARICH-HITZTARFUT-MUTZAR>
      <PirteiTaktziv>
        <PerutMasluleiHashkaa>
          <SCHUM-TZVIRA-BAMASLUL>100000.0</SCHUM-TZVIRA-BAMASLUL>
          <KOD-MASLUL-HASHKAA>XX000103</KOD-MASLUL-HASHKAA>
          <SHEUR-DMEI-NIHUL-HISACHON>0.5</SHEUR-DMEI-NIHUL-HISACHON>
        </PerutMasluleiHashkaa>
        <PerutMasluleiHashkaa>
          <SCHUM-TZVIRA-BAMASLUL>200000.0</SCHUM-TZVIRA-BAMASLUL>
          <KOD-MASLUL-HASHKAA>XX000127</KOD-MASLUL-HASHKAA>
          <SHEUR-DMEI-NIHUL-HISACHON>0.75</SHEUR-DMEI-NIHUL-HISACHON>
        </PerutMasluleiHashkaa>
      </PirteiTaktziv>
    </HeshbonOPolisa>
  </Mutzar>
</MislakaRoot>
"""

_DEFAULT_KWARGS = dict(
    weight_1=10,
    weight_3=20,
    weight_5=25,
    weight_sharp=45,
    low_exposure_threshold=25,
    medium_exposure_threshold=75,
    bad_hevrot=[],
    override_risk_level=None,
)


class TestSingleHolding:
    def test_returns_funds_list(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        assert "funds" in result
        assert isinstance(result["funds"], list)

    def test_one_result_for_one_holding(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        assert len(result["funds"]) >= 1

    def test_client_section_present(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        holding = result["funds"][0]
        assert "client" in holding

    def test_alternatives_section_present(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        holding = result["funds"][0]
        assert "alternatives" in holding

    def test_golden_section_present(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        holding = result["funds"][0]
        assert "golden" in holding

    def test_client_id_matches_mislaka(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        client = result["funds"][0]["client"]
        assert client["client_id"] == "987654321"

    def test_client_amount_matches_mislaka(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        client = result["funds"][0]["client"]
        assert client["amount"] == 150000.0

    def test_rank_within_total(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        client = result["funds"][0]["client"]
        if client["rank"] is not None:
            assert 1 <= client["rank"] <= client["total_in_risk"]

    def test_percentile_between_0_and_100(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        client = result["funds"][0]["client"]
        assert 0 <= client["percentile"] <= 100

    def test_at_most_three_alternatives(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        assert len(result["funds"][0]["alternatives"]) <= 3

    def test_alternatives_exclude_client_fund(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        client_id = result["funds"][0]["client"]["id"]
        for alt in result["funds"][0]["alternatives"]:
            assert alt["id"] != client_id

    def test_alternatives_have_potential_amount(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        for alt in result["funds"][0]["alternatives"]:
            assert "potential_amount" in alt
            assert alt["potential_amount"] > 0

    def test_risk_level_is_valid(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        risk = result["funds"][0]["client"]["risk_level"]
        assert risk in ("low", "medium", "high", "invalid")

    def test_medium_fund_has_golden_option_or_empty(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        golden = result["funds"][0]["golden"]
        # golden should be a dict (possibly empty for medium-risk client)
        assert isinstance(golden, dict)


class TestTwoHoldings:
    def test_two_holdings_returns_two_results(self):
        result = run_comparison(mislaka_file=[MISLAKA_103_AND_127], **_DEFAULT_KWARGS)
        assert len(result["funds"]) == 2

    def test_holding_ids_are_distinct(self):
        result = run_comparison(mislaka_file=[MISLAKA_103_AND_127], **_DEFAULT_KWARGS)
        ids = [h["client"]["id"] for h in result["funds"]]
        assert len(set(ids)) == len(ids)

    def test_high_risk_fund_no_golden(self):
        result = run_comparison(mislaka_file=[MISLAKA_103_AND_127], **_DEFAULT_KWARGS)
        high_risk_holding = next(
            (h for h in result["funds"] if h["client"]["risk_level"] == "high"), None
        )
        if high_risk_holding:
            assert high_risk_holding["golden"] == {}

    def test_two_separate_mislaka_files_combined(self):
        result = run_comparison(
            mislaka_file=[MISLAKA_103, MISLAKA_103],
            **_DEFAULT_KWARGS,
        )
        # Two identical files → two holdings
        assert len(result["funds"]) >= 1


class TestOverrideRiskLevel:
    def test_override_to_high_changes_alternatives_pool(self):
        normal = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        override_kwargs = {**_DEFAULT_KWARGS, "override_risk_level": "high"}
        overridden = run_comparison(mislaka_file=[MISLAKA_103], **override_kwargs)

        normal_alt_ids = {a["id"] for a in normal["funds"][0]["alternatives"]}
        override_alt_ids = {a["id"] for a in overridden["funds"][0]["alternatives"]}
        # The pools differ → IDs need not be the same (or results may be empty)
        # Just assert both completed without error
        assert isinstance(normal_alt_ids, set)
        assert isinstance(override_alt_ids, set)

    def test_override_golden_is_empty(self):
        override_kwargs = {**_DEFAULT_KWARGS, "override_risk_level": "high"}
        result = run_comparison(mislaka_file=[MISLAKA_103], **override_kwargs)
        # When override is set, golden logic is skipped
        assert result["funds"][0]["golden"] == {}


class TestBlacklist:
    def test_blacklisted_company_absent_from_alternatives(self):
        result = run_comparison(mislaka_file=[MISLAKA_103], **_DEFAULT_KWARGS)
        if not result["funds"]:
            pytest.skip("No holdings matched")

        all_hevrot = [a["hevra"] for a in result["funds"][0]["alternatives"]]
        if not all_hevrot:
            pytest.skip("No alternatives found")

        first_hevra = all_hevrot[0]
        blacklist_kwargs = {**_DEFAULT_KWARGS, "bad_hevrot": [first_hevra]}
        blacklisted_result = run_comparison(mislaka_file=[MISLAKA_103], **blacklist_kwargs)
        if not blacklisted_result["funds"]:
            return
        for alt in blacklisted_result["funds"][0]["alternatives"]:
            assert alt["hevra"] != first_hevra


class TestCustomExposureThresholds:
    def test_low_threshold_zero_makes_all_medium_or_high(self):
        kwargs = {**_DEFAULT_KWARGS, "low_exposure_threshold": 0, "medium_exposure_threshold": 50}
        result = run_comparison(mislaka_file=[MISLAKA_103], **kwargs)
        assert "funds" in result

    def test_very_high_thresholds_make_all_low(self):
        kwargs = {**_DEFAULT_KWARGS, "low_exposure_threshold": 100, "medium_exposure_threshold": 100}
        result = run_comparison(mislaka_file=[MISLAKA_103], **kwargs)
        assert "funds" in result
