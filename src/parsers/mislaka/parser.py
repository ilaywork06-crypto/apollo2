"""Parser for Mislaka (pension clearinghouse) XML files."""

# ----- Imports ----- #

import re

import lxml.etree as ET

from src.parsers.mislaka.fee_resolver import map_dmey_nihul
from src.parsers.mislaka.track_extractor import extract_track
from src.parsers.xml_utils import extract_data_from_xml

# ----- Functions ----- #


def parse_multible_mislaka_files(files: list[str]) -> list[dict]:
    """Parse multiple Mislaka file strings and combine the results.

    Args:
        files: A list of decoded Mislaka XML file strings.

    Returns:
        A flat list of investment-track dicts from all provided files.
    """
    result = []
    for file in files:
        result.extend(parse_mislaka_file(file))
    return result


def parse_mislaka_file(content: str | bytes) -> list[dict]:
    """Parse a single Mislaka XML document and extract per-track holding data.

    Strips any XML declaration before parsing (lxml requirement for
    ``fromstring``).

    Args:
        content: The Mislaka XML document as a UTF-8 string or bytes object.

    Returns:
        A list of dicts, each representing one investment track with the
        following keys: ``GEMELNET_ID``, ``SHEM-TOCHNIT``,
        ``TAARICH-HITZTARFUT-MUTZAR``, ``TOTAL-CHISACHON-MTZBR``,
        ``SHEUR-DMEI-NIHUL-TZVIRA``, ``SHEUR-DMEI-NIHUL-HAFKADA``, and
        ``KOD-MEZAHE-YATZRAN``.
    """
    if isinstance(content, str):
        content = re.sub(r"<\?xml[^?]*\?>", "", content).strip()
        content = content.encode("utf-8")

    root = ET.fromstring(content)
    dmey_nihul_tsvira_map = map_dmey_nihul(root, 1)
    dmey_nihul_hafkada_map = map_dmey_nihul(root, 2)

    # Extract client ID at file level (same for all records in this file)
    mispar_zihuy_file = "unknown"
    for lakoach in root.iter("YeshutLakoach"):
        val = extract_data_from_xml(".//MISPAR-ZIHUY-LAKOACH", lakoach)
        if val and val != "N/A":
            mispar_zihuy_file = val
        break

    list_of_funds = []
    for row in root.iter("Mutzar"):
        KOD_MEZAHE_YATZRAN = extract_data_from_xml(".//KOD-MEZAHE-YATZRAN", row)
        # Try per-Mutzar YeshutLakoach first, fall back to file-level
        mispar_zihuy = mispar_zihuy_file
        for lakoach in row.iter("YeshutLakoach"):
            val = extract_data_from_xml(".//MISPAR-ZIHUY-LAKOACH", lakoach)
            if val and val != "N/A":
                mispar_zihuy = val
            break
        for polisa in row.iter("HeshbonOPolisa"):
            SHEM_TOCHNIT = extract_data_from_xml(".//SHEM-TOCHNIT", polisa)
            TAARICH_HITZTARFUT_MUTZAR = extract_data_from_xml(
                ".//TAARICH-HITZTARFUT-MUTZAR", polisa
            )

            maslulim = polisa.findall(".//PirteiTaktziv/PerutMasluleiHashkaa")
            if not maslulim:
                maslulim = [polisa]

            for maslul in maslulim:
                track = extract_track(
                    maslul, polisa, dmey_nihul_tsvira_map, dmey_nihul_hafkada_map,
                    shem_tochnit=SHEM_TOCHNIT,
                    taarich_hitztarfut_mutzar=TAARICH_HITZTARFUT_MUTZAR,
                    kod_mezahe_yatzran=KOD_MEZAHE_YATZRAN,
                    mispar_zihuy=mispar_zihuy,
                )
                if track is not None:
                    list_of_funds.append(track)
    return list_of_funds
