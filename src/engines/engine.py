from src.parsers.mislaka_parser import parse_mislaka_file
from src.parsers.parser import parse_xml_file
import json
import copy

def find_matching_kupot(mislaka_list, kupot_list):
    matches = []
    for mislaka in mislaka_list:
        for kupa in kupot_list:
            if mislaka["GEMELNET_ID"] == kupa["ID"]:
                matches.append((mislaka, kupa))

    return matches

def get_kupot_by_risk_level(kupot_list, risk_level):
    return [kupa for kupa in kupot_list if kupa['risk_level'] == risk_level]

def apply_dmey_nihul(kupot_list, dmey_nihul):
    for kupa in kupot_list:
        kupa["tsua_5"] -= dmey_nihul
        kupa["tsua_3"] -= dmey_nihul
        kupa["tsua_mitztaberet_letkufa"] -= dmey_nihul
    return kupot_list

def normalize_data(kupot_list):
    fields = ["sharp_ribit_hasarot_sikun", "tsua_5", "tsua_3", "tsua_mitztaberet_letkufa"]
    for field in fields:
        values = [kupa[field] for kupa in kupot_list if kupa[field] != 0.0]
        min_value = min(values)
        max_value = max(values)
        for kupa in kupot_list:
            if kupa[field] != 0.0:
                kupa[field + "_normalized"] = (kupa[field] - min_value) / (max_value - min_value)* 100 if max_value > min_value else 0.0
            else:
                kupa[field + "_normalized"] = None

def calculate_grade(kupa):
    weights = {}
    if kupa.get("sharp_ribit_hasarot_sikun_normalized") is not None:
        weights["sharp_ribit_hasarot_sikun_normalized"] = 50
    if kupa.get("tsua_5_normalized") is not None:
        weights["tsua_5_normalized"] = 20
    if kupa.get("tsua_3_normalized") is not None:
        weights["tsua_3_normalized"] = 20
    if kupa.get("tsua_mitztaberet_letkufa_normalized") is not None:
        weights["tsua_mitztaberet_letkufa_normalized"] = 10

    if not weights:
        return 0

    total_weight = sum(weights.values())
    grade = 0
    for field, weight in weights.items():
        grade += kupa[field] * (weight / total_weight)

    return round(grade, 2)

def add_grade_and_sort(kupot_list):
    for kupa in kupot_list:
        kupa["grade"] = calculate_grade(kupa)
    return sorted(kupot_list, key=lambda x: x["grade"], reverse=True)

def get_top_3(sorted_kupot):
    return sorted_kupot[:3]

def get_client_ranking(sorted_kupot, client_kupa_id):
    for i, kupa in enumerate(sorted_kupot):
        if kupa["ID"] == client_kupa_id:
            return i + 1, len(sorted_kupot)
    return None, len(sorted_kupot)

def calculate_potential_amount(current_amount, current_kupa, better_kupa):
    diff = better_kupa["tsua_mitztaberet_letkufa"] - current_kupa["tsua_mitztaberet_letkufa"]
    potential = current_amount * (1 + diff / 100)
    return round(potential, 2)

def run_comparison():
    kupot_list = parse_xml_file(r'c:\Users\ilay atia\code\apollo2\src\parsers\xml2.xml')
    mislaka_list = parse_mislaka_file(r'c:\Users\ilay atia\code\apollo2\src\parsers\ilay.xml')
    matches = find_matching_kupot(mislaka_list, kupot_list)

    for mislaka, kupa in matches:
        risk_level = kupa['risk_level']
        all_kopot_in_risk_level = get_kupot_by_risk_level(kupot_list, risk_level)

        dmey_nihul = mislaka["SHEUR-DMEI-NIHUL-TZVIRA"]
        adjusted_kupot = apply_dmey_nihul(copy.deepcopy(all_kopot_in_risk_level), dmey_nihul)
        normalize_data(adjusted_kupot)
        sorted_kupot = add_grade_and_sort(adjusted_kupot)   
        top_3 = get_top_3(sorted_kupot)
        client_ranking, total_kupot = get_client_ranking(sorted_kupot, kupa["ID"])
        print(f"Rank - {client_ranking}/{total_kupot}")
        client_kupa = next(k for k in sorted_kupot if k["ID"] == kupa["ID"])
        money = mislaka["TOTAL-CHISACHON-MTZBR"]
        for better_kupa in top_3:
            if better_kupa["ID"] != client_kupa["ID"]:
                potential_amount = calculate_potential_amount(money, client_kupa, better_kupa)
                print(f"Client's Kupa: {client_kupa['shem_kupa']} (Grade: {client_kupa['grade']})")
                print(f"Better Kupa: {better_kupa['shem_kupa']} (Grade: {better_kupa['grade']})")
                print(f"Potential amount after switching: {potential_amount} NIS\n")

run_comparison()