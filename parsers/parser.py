import xml.etree.ElementTree as ET
from bidi.algorithm import get_display

def extract_data_from_xml(field_name, row):
    data = row.find(field_name)
    if data is not None:
        data = data.text
    else:
        data = "N/A"
    return data

def parse_xml_file(filename):
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
        TSUA_SHNATIT_MEMUZAAT_3_SHANIM = extract_data_from_xml('TSUA_SHNATIT_MEMUZAAT_3_SHANIM', row)

        output = f"Sug Kupa: {SUG_KUPA}\n"
        output += f"Kupa Name: {SHM_KUPA}\n"
        output += f"Company Name: {SHM_HEVRA_MENAHELET}\n"
        output += f"Hitmahut Rashit: {HITMAHUT_RASHIT}\n"
        output += f"Hitmahut Mishnit: {HITMAHUT_MISHNIT}\n"
        output += f"Tsua Shnatit Memuzaat 3 Shanim: {TSUA_SHNATIT_MEMUZAAT_3_SHANIM}\n"
        print(get_display(output))
        print("-" * 20)

parse_xml_file(r'c:\Users\ilay atia\code\apollo2\parsers\xml2.xml')
