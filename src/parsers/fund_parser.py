"""Parser for the GemeNet fund XML file (kupot_gemel_net.xml)."""

# ----- Imports ----- #

import xml.etree.ElementTree as ET
from pathlib import Path

from src.comparison.risk_classifier import RiskClassifier, split_equity_exposure
from src.parsers.xml_utils import extract_data_from_xml

# ----- Functions ----- #


def calculate_liquidity_index(net_accumulation: float, total_assets: float) -> float | None:
    """Return the fund's net 12-month accumulation as a percentage of its assets.

    A negative value means more money left the fund than entered it.

    Args:
        net_accumulation: ``TZVIRA_NETO`` — inflows minus outflows over the
            last 12 months.
        total_assets: ``YITRAT_NCHASIM_LSOF_TKUFA`` — asset balance at the end
            of the reporting period.

    Returns:
        ``net_accumulation / total_assets * 100``, or ``None`` when the fund
        reports no positive asset balance (the ratio is meaningless).
    """
    if total_assets <= 0:
        return None
    return net_accumulation / total_assets * 100


def parse_xml_file(
    content: Path,
    low_exposure_threshold: int,
    medium_exposure_threshold: int,
    risk_classifier: RiskClassifier,
    remove_special_cases: bool,
) -> list[dict]:
    """Parse the GemeNet funds XML file and return a list of fund records.

    Only rows whose ``UCHLUSIYAT_YAAD`` field equals ``"כלל האוכלוסיה"``
    (general population) are included.  Each returned dict contains
    identifiers, performance metrics, and a pre-computed risk level.

    Args:
        content: Path to the GemeNet XML file to parse.
        low_exposure_threshold: The threshold for low equity exposure.
        medium_exposure_threshold: The threshold for medium equity exposure.
        risk_classifier: Classifier used to derive each fund's risk level and
            equity exposure.
        remove_special_cases: When ``True``, only rows for the general
            population are included.

    Returns:
        A list of dicts, each representing one fund with the following keys:
        ``SUG``, ``ID``, ``tsua_mitztaberet_letkufa``,
        ``sharp_ribit_hasarot_sikun``, ``fund_name``, ``hevra``,
        ``hitmahut_rashit``, ``hitmahut_mishnit``, ``tsua_3``, ``tsua_5``,
        ``num_hevra``, ``risk_level``, ``equity_exposure``,
        ``foreign_exposure``, ``israel_equity_exposure``,
        ``israel_equity_share``, ``net_accumulation``, ``total_assets``, and
        ``liquidity_index``.
    """
    list_of_funds = []
    hey = ET.parse(content)
    root = hey.getroot()
    for row in root.findall("Row"):
        oclusia = extract_data_from_xml("UCHLUSIYAT_YAAD", row)
        if remove_special_cases and oclusia != "כלל האוכלוסיה":
            continue
        SUG_KUPA = extract_data_from_xml("SUG_KUPA", row)
        ID = extract_data_from_xml("ID", row)
        SHM_KUPA = extract_data_from_xml("SHM_KUPA", row)
        SHM_HEVRA_MENAHELET = extract_data_from_xml("SHM_HEVRA_MENAHELET", row)
        HITMAHUT_RASHIT = extract_data_from_xml("HITMAHUT_RASHIT", row)
        HITMAHUT_MISHNIT = extract_data_from_xml("HITMAHUT_MISHNIT", row)
        NUM_HEVRA = extract_data_from_xml("NUM_HEVRA", row)
        TSUA_SHNATIT_MEMUZAAT_3_SHANIM = extract_data_from_xml(
            "TSUA_SHNATIT_MEMUZAAT_3_SHANIM",
            row,
            float,
        )
        TSUA_SHNATIT_MEMUZAAT_5_SHANIM = extract_data_from_xml(
            "TSUA_SHNATIT_MEMUZAAT_5_SHANIM",
            row,
            float,
        )
        RISK_LEVEL = risk_classifier.get_risk_level(int(ID), low_exposure_threshold, medium_exposure_threshold)
        EQUITY_EXPOSURE = risk_classifier.get_equity_exposure(int(ID))
        FOREIGN_EXPOSURE = risk_classifier.get_foreign_exposure(int(ID))
        ISRAEL_EQUITY_EXPOSURE, ISRAEL_EQUITY_SHARE = split_equity_exposure(
            EQUITY_EXPOSURE, FOREIGN_EXPOSURE
        )
        TZVIRA_NETO = extract_data_from_xml("TZVIRA_NETO", row, float)
        YITRAT_NCHASIM_LSOF_TKUFA = extract_data_from_xml("YITRAT_NCHASIM_LSOF_TKUFA", row, float)
        TSUA_MITZTABERET_LETKUFA = extract_data_from_xml(
            "TSUA_MITZTABERET_LETKUFA",
            row,
            float,
        )
        SHARP_RIBIT_HASRAT_SIKUN = extract_data_from_xml(
            "SHARP_RIBIT_HASRAT_SIKUN",
            row,
            float,
        )
        list_of_funds.append(
            {
                "UCHLUSIYAT_YAAD": oclusia.strip(),
                "SUG": SUG_KUPA.strip(),
                "ID": ID.strip(),
                "tsua_mitztaberet_letkufa": TSUA_MITZTABERET_LETKUFA,
                "sharp_ribit_hasarot_sikun": SHARP_RIBIT_HASRAT_SIKUN,
                "fund_name": SHM_KUPA.strip(),
                "hevra": SHM_HEVRA_MENAHELET.strip(),
                "hitmahut_rashit": HITMAHUT_RASHIT.strip(),
                "hitmahut_mishnit": HITMAHUT_MISHNIT.strip(),
                "tsua_3": TSUA_SHNATIT_MEMUZAAT_3_SHANIM,
                "tsua_5": TSUA_SHNATIT_MEMUZAAT_5_SHANIM,
                "num_hevra": NUM_HEVRA,
                "risk_level": RISK_LEVEL,
                "equity_exposure": EQUITY_EXPOSURE,
                "foreign_exposure": FOREIGN_EXPOSURE,
                "israel_equity_exposure": ISRAEL_EQUITY_EXPOSURE,
                "israel_equity_share": ISRAEL_EQUITY_SHARE,
                "net_accumulation": TZVIRA_NETO,
                "total_assets": YITRAT_NCHASIM_LSOF_TKUFA,
                "liquidity_index": calculate_liquidity_index(TZVIRA_NETO, YITRAT_NCHASIM_LSOF_TKUFA),
            }
        )

    return list_of_funds
