from src.parsers.mislaka_parser import parse_mislaka_file
from src.parsers.parser import parse_xml_file


kupot_list = parse_xml_file(r'c:\Users\ilay atia\code\apollo2\src\parsers\xml2.xml')

mislaka_list = parse_mislaka_file(r'c:\Users\ilay atia\code\apollo2\src\parsers\ilay.xml')

def find_matching_kupot(mislaka_list, kupot_list):
    for mislaka in mislaka_list:
        for kupa in kupot_list:
            if mislaka["GEMELNET_ID"] == kupa["ID"]:
                print(f"Match found for {mislaka['SHEM-TOCHNIT']}: {kupa['shem_kupa']} , RISK LEVEL: {kupa['risk_level']} , all koput at this risk level: {len(get_kupot_by_risk_level(kupot_list, kupa['risk_level']))}")
                print()

def get_kupot_by_risk_level(kupot_list, risk_level):
    return [kupa for kupa in kupot_list if kupa['risk_level'] == risk_level]

find_matching_kupot(mislaka_list, kupot_list)