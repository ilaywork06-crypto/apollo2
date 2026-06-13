"""Builds management-fee lookups from a Mislaka document's fee-structure section."""

import lxml.etree as ET

from src.parsers.xml_utils import extract_data_from_xml


def map_dmey_nihul(root: ET._Element, sug: int) -> dict[str, float]:
    """Build a lookup of management-fee rates by investment-track code.

    Iterates over all ``PerutMivneDmeiNihul`` elements in the XML tree and
    collects fee rates for the requested expense type (``SUG-HOTZAA``).

    Args:
        root: Root lxml element of the parsed Mislaka XML document.
        sug: Expense-type code to filter on (``1`` = accumulation fee,
            ``2`` = deposit fee).

    Returns:
        A dict mapping investment-track code strings to their fee rate floats.
    """
    result = {}
    for row in root.iter("PerutMivneDmeiNihul"):
        if extract_data_from_xml(".//SUG-HOTZAA", row, int) == sug:
            kod2 = extract_data_from_xml(".//KOD-MASLUL-DMEI-NIHUL", row)
            kod = extract_data_from_xml(".//KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM", row)
            dmey = extract_data_from_xml(".//SHEUR-DMEI-NIHUL", row, float)
            result[kod] = dmey
            result[kod2] = dmey
    return result
