# ----- Imports ----- #

import xml.etree.ElementTree as ET

from src.core.risk_classifier import get_risk_level
from src.parsers.xml_utils import extract_data_from_xml

# ----- Functions ----- #


def parse_xml_file(content):
    list_of_kupot = []
    hey = ET.parse(content)
    root = hey.getroot()
    for row in root.findall("Row"):
        oclusia = extract_data_from_xml("UCHLUSIYAT_YAAD", row)
        if oclusia != "כלל האוכלוסיה":
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
        RISK_LEVEL = get_risk_level(int(ID))
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

        list_of_kupot.append(
            {
                "SUG": SUG_KUPA.strip(),
                "ID": ID.strip(),
                "tsua_mitztaberet_letkufa": TSUA_MITZTABERET_LETKUFA,
                "sharp_ribit_hasarot_sikun": SHARP_RIBIT_HASRAT_SIKUN,
                "shem_kupa": SHM_KUPA.strip(),
                "hevra": SHM_HEVRA_MENAHELET.strip(),
                "hitmahut_rashit": HITMAHUT_RASHIT.strip(),
                "hitmahut_mishnit": HITMAHUT_MISHNIT.strip(),
                "tsua_3": TSUA_SHNATIT_MEMUZAAT_3_SHANIM,
                "tsua_5": TSUA_SHNATIT_MEMUZAAT_5_SHANIM,
                "num_hevra": NUM_HEVRA,
                "risk_level": RISK_LEVEL,
            }
        )

    return list_of_kupot
