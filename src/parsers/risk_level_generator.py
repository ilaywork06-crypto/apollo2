# ----- Imports ----- #

import xml.etree.ElementTree as ET

from src.parsers.utils import extract_data_from_xml


RISKS_DICT = {}

# ----- Functions ----- #


def get_risk_level(kupa_id):
    if kupa_id not in RISKS_DICT:
        return "invalid"
    stocks_percentage = RISKS_DICT[kupa_id]
    if stocks_percentage <= 24.9999:
        return "low"
    elif 25 <= stocks_percentage <= 74.9999:
        return "medium"
    elif stocks_percentage >= 75:
        return "high"


def get_stocks_percentage_by_kupa_id(content):
    if RISKS_DICT != {}:
        return
    hey = ET.parse(content)
    root = hey.getroot()

    for row in root.findall("Row"):
        ID_KUPA = extract_data_from_xml(
            "ID_KUPA",
            row,
            int,
        )
        SHM_SUG_NECHES = extract_data_from_xml("SHM_SUG_NECHES", row)
        if SHM_SUG_NECHES == ", חשיפה למניות":
            RISKS_DICT[ID_KUPA] = extract_data_from_xml(
                "ACHUZ_SUG_NECHES",
                row,
                float,
            )
