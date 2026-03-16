import xml.etree.ElementTree as ET

RISKS_DICT = {}
def get_risk_level(kupa_id):
    if kupa_id not in RISKS_DICT.keys():
        return "invalid"
    stocks_percentage = RISKS_DICT[kupa_id]
    if stocks_percentage <= 24.9999:
        return "low"
    elif 25 <= stocks_percentage <= 74.9999:
        return "medium"
    elif stocks_percentage >= 75:
        return "high"

def extract_data_from_xml(field_name, row, field_type=str):
    data = row.find(field_name)
    if data is not None and data.text is not None:
        return field_type(data.text)
    return "N/A" if field_type == str else 0.0

def get_stocks_percentage_by_kupa_id(content):
    if RISKS_DICT != {}:
        return
    hey = ET.parse(content)
    root = hey.getroot()
    
    for row in root.findall('Row'):
        ID_KUPA = extract_data_from_xml('ID_KUPA', row, int)
        SHM_SUG_NECHES = extract_data_from_xml('SHM_SUG_NECHES', row)
        if SHM_SUG_NECHES == ", חשיפה למניות":
            RISKS_DICT[ID_KUPA] = extract_data_from_xml('ACHUZ_SUG_NECHES', row, float)
