"""Parser for the GemeNet fund XML file (kupot_gemel_net.xml)."""

# ----- Imports ----- #

import xml.etree.ElementTree as ET
from pathlib import Path

from src.core.risk_classifier import get_equity_exposure, get_risk_level
from src.parsers.xml_utils import extract_data_from_xml

# ----- Functions ----- #

def remove_bad_hevrot(list_of_funds: list[dict], bad_hevrot: list[str]) -> list[dict]:
    """Remove records with invalid or excluded company names.

    Args:
        list_of_funds: A list of fund dicts, each containing a ``hevra`` key.
        bad_hevrot: A set of company names to exclude.

    Returns:
        A filtered list of fund dicts, excluding those whose ``hevra`` value
        is in the predefined set of bad company names.
    """
    return [fund for fund in list_of_funds if fund["hevra"] not in bad_hevrot]

def parse_xml_file(content: Path, low_exposure_threshold: int, medium_exposure_threshold: int, bad_hevrot: list[str], remove_special_cases: bool) -> list[dict]:
    """Parse the GemeNet funds XML file and return a list of fund records.

    Only rows whose ``UCHLUSIYAT_YAAD`` field equals ``"כלל האוכלוסיה"``
    (general population) are included.  Each returned dict contains
    identifiers, performance metrics, and a pre-computed risk level.

    Args:
        content: Path to the GemeNet XML file to parse.
        low_exposure_threshold: The threshold for low equity exposure.
        medium_exposure_threshold: The threshold for medium equity exposure.

    Returns:
        A list of dicts, each representing one fund with the following keys:
        ``SUG``, ``ID``, ``tsua_mitztaberet_letkufa``,
        ``sharp_ribit_hasarot_sikun``, ``fund_name``, ``hevra``,
        ``hitmahut_rashit``, ``hitmahut_mishnit``, ``tsua_3``, ``tsua_5``,
        ``num_hevra``, and ``risk_level``.
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
        RISK_LEVEL = get_risk_level(int(ID), low_exposure_threshold, medium_exposure_threshold)
        EQUITY_EXPOSURE = get_equity_exposure(int(ID))
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
            }
        )

    return remove_bad_hevrot(list_of_funds, bad_hevrot)
