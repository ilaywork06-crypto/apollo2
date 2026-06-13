"""Classifies a fund's equity-exposure risk level from a risks map."""

from pathlib import Path


class RiskClassifier:
    """Looks up a fund's equity exposure and derives a risk-level label.

    Risk bands:
    * ``"low"``    — equity exposure <= low_exposure_threshold
    * ``"medium"`` — equity exposure <= medium_exposure_threshold
    * ``"high"``   — equity exposure > medium_exposure_threshold
    * ``"invalid"`` — fund ID not found in the risk map
    """

    def __init__(self, risks: dict[int, float] | None = None, path: Path | None = None) -> None:
        """Construct a classifier from an in-memory map or an XML file.

        Args:
            risks: A pre-built fund-ID to equity-exposure mapping.
            path: Filesystem path to the risks-map XML file, used to build
                the mapping when *risks* is not provided.

        Raises:
            ValueError: If neither *risks* nor *path* is given.
        """
        if risks is not None:
            self._risks = dict(risks)
        elif path is not None:
            from src.parsers.risk_map_parser import parse_risk_map
            self._risks = parse_risk_map(path)
        else:
            raise ValueError("RiskClassifier requires either 'risks' or 'path'")

    def get_equity_exposure(self, fund_id: int) -> float | None:
        """Return the raw equity-exposure percentage for a fund, or None if unknown."""
        return self._risks.get(fund_id)

    def get_risk_level(
        self, fund_id: int, low_exposure_threshold: float, medium_exposure_threshold: float
    ) -> str:
        """Return the risk-level label for a fund based on its equity exposure."""
        if fund_id not in self._risks:
            return "invalid"
        pct = self._risks[fund_id]
        if pct <= low_exposure_threshold:
            return "low"
        elif pct <= medium_exposure_threshold:
            return "medium"
        else:
            return "high"
