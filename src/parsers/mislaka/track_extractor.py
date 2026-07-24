"""Builds a single investment-track record from a Mislaka PerutMasluleiHashkaa element."""

import lxml.etree as ET

from src.parsers.xml_utils import extract_data_from_xml

# Tracks holding less than this balance (in NIS) are residual/dead accounts
# (e.g. a one-agora leftover) and are excluded from comparison.
MIN_TRACK_BALANCE = 1.0


def extract_track(
    maslul: ET._Element,
    polisa: ET._Element,
    tzvira_fees: dict[str, float],
    hafkada_fees: dict[str, float],
    uniform_tzvira_fee: float,
    uniform_hafkada_fee: float,
    *,
    shem_tochnit: str,
    taarich_hitztarfut_mutzar: str,
    kod_mezahe_yatzran: str,
    mispar_zihuy: str,
) -> dict | None:
    """Build one investment-track record, or ``None`` if it holds no balance.

    Management fees are resolved by taking the maximum of the
    structure-level fee and the track-level fee to ensure the most
    conservative (highest-cost) assumption is used.

    Args:
        maslul: The ``PerutMasluleiHashkaa`` (or ``HeshbonOPolisa`` fallback)
            element describing a single investment track.
        polisa: The enclosing ``HeshbonOPolisa`` element, used to resolve
            policy-level deposit-fee fields.
        tzvira_fees: Accumulation-fee rates keyed by investment-track code
            (from :func:`src.parsers.mislaka.fee_resolver.map_dmey_nihul`).
        hafkada_fees: Deposit-fee rates keyed by investment-track code.
        uniform_tzvira_fee: Policy-wide accumulation fee that applies when the
            producer declares uniform fees but omits the per-track key (from
            :func:`src.parsers.mislaka.fee_resolver.resolve_uniform_dmey_nihul`).
        uniform_hafkada_fee: Policy-wide deposit fee, resolved the same way.
        shem_tochnit: The plan name for this policy.
        taarich_hitztarfut_mutzar: The product join date for this policy.
        kod_mezahe_yatzran: The producer identifier for this Mutzar.
        mispar_zihuy: The client identifier for this holding.

    Returns:
        A dict with the track's ``GEMELNET_ID``, ``SHEM-TOCHNIT``,
        ``TAARICH-HITZTARFUT-MUTZAR``, ``TOTAL-CHISACHON-MTZBR``,
        ``SHEUR-DMEI-NIHUL-TZVIRA``, ``SHEUR-DMEI-NIHUL-HAFKADA``,
        ``KOD-MEZAHE-YATZRAN``, and ``MISPAR-ZIHUY-LAKOACH`` keys, or ``None``
        if the track holds a negligible balance (below :data:`MIN_TRACK_BALANCE`).
    """
    SCHUM_TZVIRA_BAMASLUL = extract_data_from_xml(".//SCHUM-TZVIRA-BAMASLUL", maslul, float)
    if SCHUM_TZVIRA_BAMASLUL < MIN_TRACK_BALANCE:
        return None

    KOD_MASLUL_HASHKAA = extract_data_from_xml(".//KOD-MASLUL-HASHKAA", maslul)

    FINAL_DMEI_NIHUL_TZVIRA = max(
        tzvira_fees.get(KOD_MASLUL_HASHKAA, 0.0),
        uniform_tzvira_fee,
        extract_data_from_xml(".//SHEUR-DMEI-NIHUL-TZVIRA", maslul, float),
        extract_data_from_xml(".//SHEUR-DMEI-NIHUL-HISACHON", maslul, float),
    )
    # if FINAL_DMEI_NIHUL_TZVIRA == 0.0:
    #     FINAL_DMEI_NIHUL_TZVIRA = extract_data_from_xml(
    #         ".//SHIUR-ALUT-SHNATIT-ZPUIA-LMSLUL-HASHKAH", maslul, float
    #     )
    FINAL_DMEI_NIHUL_HAFKADA = max(
        hafkada_fees.get(KOD_MASLUL_HASHKAA, 0.0),
        uniform_hafkada_fee,
        extract_data_from_xml(".//SHEUR-DMEI-NIHUL-HAFKADA-MIVNE", polisa, float),
        extract_data_from_xml(".//SHEUR-DMEI-NIHUL-HAFKADA", polisa, float),
    )

    kod_maslul = "fr"
    if KOD_MASLUL_HASHKAA[-6:] != "N/A":
        kod_maslul = str(int(KOD_MASLUL_HASHKAA[-6:])).strip()

    return {
        "GEMELNET_ID": kod_maslul,
        "SHEM-TOCHNIT": shem_tochnit.strip(),
        "TAARICH-HITZTARFUT-MUTZAR": taarich_hitztarfut_mutzar.strip(),
        "TOTAL-CHISACHON-MTZBR": SCHUM_TZVIRA_BAMASLUL,
        "SHEUR-DMEI-NIHUL-TZVIRA": FINAL_DMEI_NIHUL_TZVIRA,
        "SHEUR-DMEI-NIHUL-HAFKADA": FINAL_DMEI_NIHUL_HAFKADA,
        "KOD-MEZAHE-YATZRAN": kod_mezahe_yatzran.strip(),
        "MISPAR-ZIHUY-LAKOACH": mispar_zihuy,
    }
