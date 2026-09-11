"""Unit tests for src/parsers/mislaka/track_extractor.py"""

import lxml.etree as ET
import pytest

from src.parsers.mislaka.track_extractor import MIN_TRACK_BALANCE, extract_track


def _track(balance="1000.0", code="XX000777", **fields):
    extra = "".join(f"<{k.replace('_', '-')}>{v}</{k.replace('_', '-')}>" for k, v in fields.items())
    code_el = f"<KOD-MASLUL-HASHKAA>{code}</KOD-MASLUL-HASHKAA>" if code is not None else ""
    return ET.fromstring(
        f"<PerutMasluleiHashkaa><SCHUM-TZVIRA-BAMASLUL>{balance}</SCHUM-TZVIRA-BAMASLUL>{code_el}{extra}</PerutMasluleiHashkaa>"
    )


def _polisa(**fields):
    extra = "".join(f"<{k.replace('_', '-')}>{v}</{k.replace('_', '-')}>" for k, v in fields.items())
    return ET.fromstring(f"<HeshbonOPolisa>{extra}</HeshbonOPolisa>")


def _extract(maslul, polisa=None, tzvira=None, hafkada=None, uniform_tzvira=0.0, uniform_hafkada=0.0):
    return extract_track(
        maslul, polisa if polisa is not None else _polisa(), tzvira or {}, hafkada or {},
        uniform_tzvira, uniform_hafkada,
        shem_tochnit=" Plan ", taarich_hitztarfut_mutzar=" 20200101 ",
        kod_mezahe_yatzran=" Y1 ", mispar_zihuy="123", shem_lakoach="דנה",
    )


class TestBalanceThreshold:
    def test_threshold_is_one_shekel(self):
        assert MIN_TRACK_BALANCE == 1.0

    @pytest.mark.parametrize("balance", ["1.0", "1.2", "38.70"])
    def test_live_balances_are_kept(self, balance):
        assert _extract(_track(balance))["TOTAL-CHISACHON-MTZBR"] == float(balance)

    @pytest.mark.parametrize("balance", ["0.99", "0.01", "0.0"])
    def test_residual_balances_are_dropped(self, balance):
        assert _extract(_track(balance)) is None


class TestAccumulationFee:
    def test_takes_the_highest_of_all_sources(self):
        maslul = _track(SHEUR_DMEI_NIHUL_TZVIRA="0.4", SHEUR_DMEI_NIHUL_HISACHON="0.3")
        record = _extract(maslul, tzvira={"XX000777": 0.6}, uniform_tzvira=0.5)
        assert record["SHEUR-DMEI-NIHUL-TZVIRA"] == 0.6

    @pytest.mark.parametrize("source", ["SHEUR_DMEI_NIHUL_TZVIRA", "SHEUR_DMEI_NIHUL_HISACHON"])
    def test_track_level_sources(self, source):
        assert _extract(_track(**{source: "0.81"}))["SHEUR-DMEI-NIHUL-TZVIRA"] == 0.81

    def test_uniform_policy_fee(self):
        assert _extract(_track(), uniform_tzvira=0.33)["SHEUR-DMEI-NIHUL-TZVIRA"] == 0.33

    def test_implausibly_low_fee_falls_back_to_the_expected_annual_cost(self):
        maslul = _track(SHEUR_DMEI_NIHUL_HISACHON="0.1", SHIUR_ALUT_SHNATIT_ZPUIA_LMSLUL_HASHKAH="0.62")
        assert _extract(maslul)["SHEUR-DMEI-NIHUL-TZVIRA"] == 0.62

    @pytest.mark.parametrize("fee", ["0.125", "0.15"])
    def test_fees_from_the_threshold_up_are_kept(self, fee):
        maslul = _track(SHEUR_DMEI_NIHUL_HISACHON=fee, SHIUR_ALUT_SHNATIT_ZPUIA_LMSLUL_HASHKAH="0.62")
        assert _extract(maslul)["SHEUR-DMEI-NIHUL-TZVIRA"] == float(fee)


class TestDepositFee:
    def test_takes_the_highest_of_all_sources(self):
        polisa = _polisa(SHEUR_DMEI_NIHUL_HAFKADA_MIVNE="1.5", SHEUR_DMEI_NIHUL_HAFKADA="2.0")
        record = _extract(_track(), polisa, hafkada={"XX000777": 1.0}, uniform_hafkada=1.2)
        assert record["SHEUR-DMEI-NIHUL-HAFKADA"] == 2.0

    @pytest.mark.parametrize("source", ["SHEUR_DMEI_NIHUL_HAFKADA_MIVNE", "SHEUR_DMEI_NIHUL_HAFKADA"])
    def test_policy_level_sources(self, source):
        assert _extract(_track(), _polisa(**{source: "3.1"}))["SHEUR-DMEI-NIHUL-HAFKADA"] == 3.1

    def test_keyed_and_uniform_sources(self):
        assert _extract(_track(), hafkada={"XX000777": 1.7})["SHEUR-DMEI-NIHUL-HAFKADA"] == 1.7
        assert _extract(_track(), uniform_hafkada=0.9)["SHEUR-DMEI-NIHUL-HAFKADA"] == 0.9


class TestRecord:
    def test_full_record(self):
        assert _extract(_track("5000.5", code="XX012345", SHEUR_DMEI_NIHUL_HISACHON="0.5")) == {
            "GEMELNET_ID": "12345",
            "SHEM-TOCHNIT": "Plan",
            "TAARICH-HITZTARFUT-MUTZAR": "20200101",
            "TOTAL-CHISACHON-MTZBR": 5000.5,
            "SHEUR-DMEI-NIHUL-TZVIRA": 0.5,
            "SHEUR-DMEI-NIHUL-HAFKADA": 0.0,
            "KOD-MEZAHE-YATZRAN": "Y1",
            "MISPAR-ZIHUY-LAKOACH": "123",
            "SHEM-LAKOACH": "דנה",
        }

    def test_uses_the_last_six_digits_of_the_track_code(self):
        assert _extract(_track(code="9990000154"))["GEMELNET_ID"] == "154"

    def test_missing_track_code(self):
        assert _extract(_track(code=None))["GEMELNET_ID"] == "fr"
