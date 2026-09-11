"""Parser for the risks-map XML file that maps fund IDs to asset-exposure percentages."""

import xml.etree.ElementTree as ET
from pathlib import Path

from src.parsers.xml_utils import extract_data_from_xml

EQUITY_EXPOSURE = ", חשיפה למניות"
FOREIGN_EXPOSURE = 'חשיפה לחו"ל'


def parse_exposure_maps(path: Path) -> tuple[dict[int, float], dict[int, float]]:
    """Parse the risks-map XML once and return its equity and foreign exposures.

    Only rows whose ``SHM_SUG_NECHES`` field equals ``", חשיפה למניות"``
    (equity exposure) or ``'חשיפה לחו"ל'`` (foreign exposure) are used.

    Args:
        path: Filesystem path to the risks-map XML file.

    Returns:
        A ``(equity, foreign)`` pair of dicts, each mapping fund ID integers to
        exposure-percentage floats.
    """
    equity: dict[int, float] = {}
    foreign: dict[int, float] = {}
    root = ET.parse(path).getroot()
    for row in root.findall("Row"):
        asset_type = extract_data_from_xml("SHM_SUG_NECHES", row)
        if asset_type == EQUITY_EXPOSURE:
            target = equity
        elif asset_type == FOREIGN_EXPOSURE:
            target = foreign
        else:
            continue
        fund_id = extract_data_from_xml("ID_KUPA", row, int)
        target[fund_id] = extract_data_from_xml("ACHUZ_SUG_NECHES", row, float)
    return equity, foreign


def parse_risk_map(path: Path) -> dict[int, float]:
    """Parse the risks-map XML and return a fund-ID to equity-exposure mapping.

    Only rows whose ``SHM_SUG_NECHES`` field equals ``", חשיפה למניות"``
    (equity exposure) are included.

    Args:
        path: Filesystem path to the risks-map XML file.

    Returns:
        A dict mapping fund ID integers to their equity-exposure percentage
        floats.
    """
    return parse_exposure_maps(path)[0]
