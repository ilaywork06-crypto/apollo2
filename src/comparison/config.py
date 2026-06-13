"""Static configuration: data file paths and default comparison weights."""

from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
GEMEL_NET_PATH = _DATA_DIR / "kupot_gemel_net.xml"
RISKS_MAP_PATH = _DATA_DIR / "risks_map.xml"

# Fixed default weights used for community comparisons (fair, user-independent)
DEFAULT_WEIGHT_1 = 10
DEFAULT_WEIGHT_3 = 20
DEFAULT_WEIGHT_5 = 25
DEFAULT_WEIGHT_SHARP = 45
