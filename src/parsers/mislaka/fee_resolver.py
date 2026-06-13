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


def resolve_uniform_dmey_nihul(polisa: ET._Element, sug: int) -> float:
    """Resolve the management-fee rate for a policy that declares uniform fees.

    When a producer marks ``DMEI-NIHUL-ACHIDIM = 1`` (fees are uniform across
    all investment tracks), the Mislaka spec makes the per-track key
    ``KOD-MASLUL-HASHKAA-BAAL-DMEI-NIHUL-YECHUDIIM`` optional -- it is only
    required when fees differ between tracks (``DMEI-NIHUL-ACHIDIM = 2``). Some
    producers (e.g. Harel) omit that key entirely, so the keyed lookup built by
    :func:`map_dmey_nihul` cannot find the rate and the track is left with a
    zero fee. In that situation the single ``SHEUR-DMEI-NIHUL`` rate applies to
    every track in the policy, so this recovers it as a policy-wide fallback.

    Args:
        polisa: A ``HeshbonOPolisa`` element whose ``PerutMivneDmeiNihul``
            fee-structure rows are inspected.
        sug: Expense-type code to filter on (``1`` = accumulation fee,
            ``2`` = deposit fee).

    Returns:
        The highest uniform fee rate declared for the requested expense type,
        or ``0.0`` when the policy declares no uniform fee for it.
    """
    result = 0.0
    for row in polisa.iter("PerutMivneDmeiNihul"):
        if extract_data_from_xml(".//SUG-HOTZAA", row, int) != sug:
            continue
        if extract_data_from_xml(".//DMEI-NIHUL-ACHIDIM", row, int) == 1:
            result = max(result, extract_data_from_xml(".//SHEUR-DMEI-NIHUL", row, float))
    return result
