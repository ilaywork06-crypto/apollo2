import xml.etree.ElementTree as ET

def extract_data_from_xml(field_name, row, field_type=str):
    data = row.find(field_name)
    if data is not None and data.text is not None:
        return field_type(data.text)
    return "N/A" if field_type == str else 0.0

def parse_multible_mislaka_files(files):
    mother_list = []
    for file in files:
        child_list = parse_mislaka_file(file)
        for one in child_list:
            mother_list.append(one)
    return mother_list

def parse_mislaka_file(content):
    list_of_kupot = []
    root = ET.fromstring(content)
    mutzar = root.iter('Mutzar')
    for row in mutzar:
        KOD_MEZAHE_YATZRAN = extract_data_from_xml('.//KOD-MEZAHE-YATZRAN', row)
        for polisa in row.iter('HeshbonOPolisa'):
            KOD_MASLUL_HASHKAA = extract_data_from_xml('.//PerutMasluleiHashkaa/KOD-MASLUL-HASHKAA', polisa)
            SHEM_TOCHNIT = extract_data_from_xml('.//SHEM-TOCHNIT', polisa)
            TAARICH_HITZTARFUT_MUTZAR = extract_data_from_xml('.//TAARICH-HITZTARFUT-MUTZAR', polisa)
            TOTAL_CHISACHON_MTZBR = extract_data_from_xml('.//TOTAL-CHISACHON-MTZBR', polisa, float)
            SHEUR_DMEI_NIHUL_TZVIRA = 0.0
            for mivne in polisa.iter('PerutMivneDmeiNihul'):
                sug = mivne.find('SUG-HOTZAA')
                if sug is not None and sug.text == '1':
                    sheur = mivne.find('SHEUR-DMEI-NIHUL')
                    if sheur is not None and sheur.text:
                        SHEUR_DMEI_NIHUL_TZVIRA = float(sheur.text)

                    break

            SHEUR_DMEI_NIHUL_HAFKADA = extract_data_from_xml('.//SHEUR-DMEI-NIHUL-HAFKADA', polisa, float)
            kod_maslul = "fr"
            if KOD_MASLUL_HASHKAA[-6:] != 'N/A':
                kod_maslul = str(int(KOD_MASLUL_HASHKAA[-6:])).strip()
            list_of_kupot.append({
                "GEMELNET_ID": kod_maslul,
    "SHEM-TOCHNIT": SHEM_TOCHNIT.strip(),
    "TAARICH-HITZTARFUT-MUTZAR": TAARICH_HITZTARFUT_MUTZAR.strip(),
    "TOTAL-CHISACHON-MTZBR": TOTAL_CHISACHON_MTZBR,
    "SHEUR-DMEI-NIHUL-TZVIRA": SHEUR_DMEI_NIHUL_TZVIRA,
    "SHEUR-DMEI-NIHUL-HAFKADA": SHEUR_DMEI_NIHUL_HAFKADA,
    "KOD-MEZAHE-YATZRAN": KOD_MEZAHE_YATZRAN.strip(),
})

    return list_of_kupot

