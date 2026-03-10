import xml.etree.ElementTree as ET

RISK_LEVELS = {
    "low": {'אג"ח', 'אג"ח ממשלות', 'אג"ח סחיר', 'אג"ח ללא מניות', 'אשראי ואג"ח', 'כספי (שקלי)', 'מדד ללא מניות', 'עוקב מדדי אג"ח'},
    "medium": {'כללי', 'משולב סחיר', 'עוקב מדדים - גמיש', 'קיימות', 'הלכה יהודית',  'הלכה איסלאמית'},
    "high": {'מניות', 'מניות סחיר',  'עוקב מדדי מניות', 'חו"ל', 'עוקב מדד s&p 500' }
}

def get_risk_level(hitmahut_mishnit):
    for level, types in RISK_LEVELS.items():
        if hitmahut_mishnit in types:
            return level
    return "unknown"

def extract_data_from_xml(field_name, row, field_type=str):
    data = row.find(field_name)
    if data is not None and data.text is not None:
        return field_type(data.text)
    return "N/A" if field_type == str else 0.0

def parse_xml_file(filename):
    list_of_kupot = []
    tree = ET.parse(filename)
    root = tree.getroot()
    print(f"Root tag: {root.tag}\n")
    for row in root.findall('Row'):
        SUG_KUPA = extract_data_from_xml('SUG_KUPA', row)
        if SUG_KUPA != 'קופת גמל להשקעה':
            continue
        
        SHM_KUPA = extract_data_from_xml('SHM_KUPA', row)
        SHM_HEVRA_MENAHELET = extract_data_from_xml('SHM_HEVRA_MENAHELET', row)
        HITMAHUT_RASHIT = extract_data_from_xml('HITMAHUT_RASHIT', row)
        HITMAHUT_MISHNIT = extract_data_from_xml('HITMAHUT_MISHNIT', row)
        TSUA_SHNATIT_MEMUZAAT_3_SHANIM = extract_data_from_xml('TSUA_SHNATIT_MEMUZAAT_3_SHANIM', row, float)
        TSUA_SHNATIT_MEMUZAAT_5_SHANIM = extract_data_from_xml('TSUA_SHNATIT_MEMUZAAT_5_SHANIM', row, float)
        RISK_LEVEL = get_risk_level(HITMAHUT_MISHNIT.strip())

        list_of_kupot.append({
    "shem_kupa": SHM_KUPA.strip(),
    "hevra": SHM_HEVRA_MENAHELET.strip(),
    "hitmahut_rashit": HITMAHUT_RASHIT.strip(),
    "hitmahut_mishnit": HITMAHUT_MISHNIT.strip(),
    "tsua_3": TSUA_SHNATIT_MEMUZAAT_3_SHANIM,
    "tsua_5": TSUA_SHNATIT_MEMUZAAT_5_SHANIM,
    "risk_level": RISK_LEVEL
})

    return list_of_kupot

kupot_list = parse_xml_file(r'c:\Users\ilay atia\code\apollo2\parsers\xml2.xml')
print("Total high risk kupot found:", sum(1 for kupa in kupot_list if kupa['risk_level'] == 'high'))
print("Total medium risk kupot found:", sum(1 for kupa in kupot_list if kupa['risk_level'] == 'medium'))
print("Total low risk kupot found:", sum(1 for kupa in kupot_list if kupa['risk_level'] == 'low'))