# ----- Imports ----- #

import re

import lxml.etree as ET

# ----- Functions ----- #


def extract_data_from_xml(
    field_name,
    row,
    field_type=str,
    ):
    data = row.find(field_name)
    if data is not None and data.text is not None:
        return field_type(data.text)
    return "N/A" if field_type is str else 0.0


def parse_multible_mislaka_files(files):
    mother_list = []
    for file in files:
        child_list = parse_mislaka_file(file)
        for one in child_list:
            mother_list.append(one)
    return mother_list

def map_dmey_nuhul_tsvira(content):
    my_map = {}
    root = ET.fromstring(content)
    rows = root.iter("PerutMivneDmeiNihul")
    for row in rows:
        SUG = extract_data_from_xml(".//SUG-HOTZAA", row, int)
        DMEY_NIHUL = extract_data_from_xml(".//SHEUR-DMEI-NIHUL", row, float)
        KOD = extract_data_from_xml(".//KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM", row)
        if SUG == 1:
            my_map[KOD] = DMEY_NIHUL
    return my_map




def map_dmey_nihul_hafkada(content):
    my_map = {}
    root = ET.fromstring(content)
    rows = root.iter("PerutMivneDmeiNihul")
    for row in rows:
        SUG = extract_data_from_xml(".//SUG-HOTZAA", row, int)
        DMEY_NIHUL = extract_data_from_xml(".//SHEUR-DMEI-NIHUL", row, float)
        KOD = extract_data_from_xml(".//KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM", row)
        if SUG == 2:
            my_map[KOD] = DMEY_NIHUL
    return my_map

def get_dmey_nihul_by_id(map, id):
    if id in map.keys():
        return map[id]
    else:
        return 0.0

def pick_dmey_nihul(list_of_numbers):
    return max(list_of_numbers)

def parse_mislaka_file(content):
    if isinstance(content, str):
        content = re.sub(
            r"<\?xml[^?]*\?>",
            "",
            content,
        ).strip()
        content = content.encode("utf-8")
    dmey_nihul_tsvira_map = map_dmey_nuhul_tsvira(content)
    dmey_nihul_hafkada_map = map_dmey_nihul_hafkada(content)
    list_of_kupot = []
    root = ET.fromstring(content)
    mutzar = root.iter("Mutzar")
    for row in mutzar:
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
                    ".//SCHUM-TZVIRA-BAMASLUL",
                    maslul,
                    float,
                )
                KOD_MASLUL_HASHKAA = extract_data_from_xml(".//KOD-MASLUL-HASHKAA", maslul)
                SHEUR_DMEI_NIHUL_TZVIRA_FROM_MIVNE = get_dmey_nihul_by_id(dmey_nihul_tsvira_map, KOD_MASLUL_HASHKAA)
                SHEUR_DMEI_NIHUL_HAFKADA_FROM_MIVNE = get_dmey_nihul_by_id(dmey_nihul_hafkada_map, KOD_MASLUL_HASHKAA)
                SHEUR_DMEI_NIHUL_TZVIRA_FROM_MASLUL_MIVNE = extract_data_from_xml(
                    ".//SHEUR-DMEI-NIHUL-HISACHON-MIVNE",
                    maslul,
                    float,
                )
                SHEUR_DMEI_NIHUL_HAFKADA_FROM_MASLUL_MIVNE = extract_data_from_xml(
                    ".//SHEUR-DMEI-NIHUL-HAFKADA-MIVNE",
                    polisa,
                    float,
                )
                SHEUR_DMEI_NIHUL_TZVIRA_FROM_MASLUL = extract_data_from_xml(
                    ".//SHEUR-DMEI-NIHUL-HISACHON",
                    maslul,
                    float,
                )
                SHEUR_DMEI_NIHUL_HAFKADA_FROM_MASLUL = extract_data_from_xml(
                    ".//SHEUR-DMEI-NIHUL-HAFKADA",
                    polisa,
                    float,
                )
                DMEI_NIHUL_ACHERIM = extract_data_from_xml(
                    ".//DMEI-NIHUL-ACHERIM",
                    polisa,
                    float
                )
                FINAL_DMEI_NIHUL_HAFKADA = pick_dmey_nihul([
                    SHEUR_DMEI_NIHUL_HAFKADA_FROM_MIVNE,
                    SHEUR_DMEI_NIHUL_HAFKADA_FROM_MASLUL_MIVNE,
                    SHEUR_DMEI_NIHUL_HAFKADA_FROM_MASLUL]
                    )
                FINAL_DMEI_NIHUL_TZVIRA = pick_dmey_nihul([
                    SHEUR_DMEI_NIHUL_TZVIRA_FROM_MIVNE,
                    SHEUR_DMEI_NIHUL_TZVIRA_FROM_MASLUL_MIVNE,
                    SHEUR_DMEI_NIHUL_TZVIRA_FROM_MASLUL]
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
