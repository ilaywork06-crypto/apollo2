import xml.etree.ElementTree as ET

from src.parsers.xml_utils import extract_data_from_xml


def parse_risk_map(path) -> dict:
    """Returns {kupa_id (int): stock_exposure_pct (float)}"""
    result = {}
    root = ET.parse(path).getroot()
    for row in root.findall("Row"):
        if extract_data_from_xml("SHM_SUG_NECHES", row) == ", חשיפה למניות":
            kupa_id = extract_data_from_xml("ID_KUPA", row, int)
            percentage = extract_data_from_xml("ACHUZ_SUG_NECHES", row, float)
            result[kupa_id] = percentage
    return result
