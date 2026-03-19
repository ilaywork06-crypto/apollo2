# ----- Imports ----- #

import re

import lxml.etree as ET

from src.parsers.xml_utils import extract_data_from_xml

# ----- Functions ----- #


def _map_dmey_nihul(root, sug):
    result = {}
    for row in root.iter("PerutMivneDmeiNihul"):
        if extract_data_from_xml(".//SUG-HOTZAA", row, int) == sug:
            kod = extract_data_from_xml(".//KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM", row)
            dmey = extract_data_from_xml(".//SHEUR-DMEI-NIHUL", row, float)
            result[kod] = dmey
    return result


def parse_multible_mislaka_files(files):
    result = []
    for file in files:
        result.extend(parse_mislaka_file(file))
    return result


def parse_mislaka_file(content):
    if isinstance(content, str):
        content = re.sub(r"<\?xml[^?]*\?>", "", content).strip()
        content = content.encode("utf-8")

    root = ET.fromstring(content)
    dmey_nihul_tsvira_map = _map_dmey_nihul(root, 1)
    dmey_nihul_hafkada_map = _map_dmey_nihul(root, 2)

    list_of_kupot = []
    for row in root.iter("Mutzar"):
        KOD_MEZAHE_YATZRAN = extract_data_from_xml(".//KOD-MEZAHE-YATZRAN", row)
        for polisa in row.iter("HeshbonOPolisa"):
            SHEM_TOCHNIT = extract_data_from_xml(".//SHEM-TOCHNIT", polisa)
            TAARICH_HITZTARFUT_MUTZAR = extract_data_from_xml(
                ".//TAARICH-HITZTARFUT-MUTZAR", polisa
            )

            maslulim = polisa.findall(".//PirteiTaktziv/PerutMasluleiHashkaa")
            if not maslulim:
                maslulim = [polisa]

            for maslul in maslulim:
                SCHUM_TZVIRA_BAMASLUL = extract_data_from_xml(
                    ".//SCHUM-TZVIRA-BAMASLUL", maslul, float
                )
                KOD_MASLUL_HASHKAA = extract_data_from_xml(".//KOD-MASLUL-HASHKAA", maslul)

                FINAL_DMEI_NIHUL_TZVIRA = max(
                    dmey_nihul_tsvira_map.get(KOD_MASLUL_HASHKAA, 0.0),
                    extract_data_from_xml(".//SHEUR-DMEI-NIHUL-HISACHON-MIVNE", maslul, float),
                    extract_data_from_xml(".//SHEUR-DMEI-NIHUL-HISACHON", maslul, float),
                )
                FINAL_DMEI_NIHUL_HAFKADA = max(
                    dmey_nihul_hafkada_map.get(KOD_MASLUL_HASHKAA, 0.0),
                    extract_data_from_xml(".//SHEUR-DMEI-NIHUL-HAFKADA-MIVNE", polisa, float),
                    extract_data_from_xml(".//SHEUR-DMEI-NIHUL-HAFKADA", polisa, float),
                )

                kod_maslul = "fr"
                if KOD_MASLUL_HASHKAA[-6:] != "N/A":
                    kod_maslul = str(int(KOD_MASLUL_HASHKAA[-6:])).strip()

                list_of_kupot.append(
                    {
                        "GEMELNET_ID": kod_maslul,
                        "SHEM-TOCHNIT": SHEM_TOCHNIT.strip(),
                        "TAARICH-HITZTARFUT-MUTZAR": TAARICH_HITZTARFUT_MUTZAR.strip(),
                        "TOTAL-CHISACHON-MTZBR": SCHUM_TZVIRA_BAMASLUL,
                        "SHEUR-DMEI-NIHUL-TZVIRA": FINAL_DMEI_NIHUL_TZVIRA,
                        "SHEUR-DMEI-NIHUL-HAFKADA": FINAL_DMEI_NIHUL_HAFKADA,
                        "KOD-MEZAHE-YATZRAN": KOD_MEZAHE_YATZRAN.strip(),
                    }
                )
    return list_of_kupot
