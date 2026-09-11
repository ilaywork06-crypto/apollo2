"""Classifies a fund's equity-exposure risk level from a risks map."""

from pathlib import Path


def split_equity_exposure(
    equity: float | None, foreign: float | None
) -> tuple[float | None, float | None]:
    """Split a fund's equity exposure into its Israeli part and its share of the equity.

    Israeli equity is taken as equity exposure minus foreign exposure. Foreign
    exposure also covers non-equity assets held abroad (e.g. foreign bonds), so
    it can exceed the equity exposure; the Israeli part is therefore floored
    at ``0`` (and capped at the total equity).

    Args:
        equity: The fund's equity-exposure percentage, or ``None`` if unknown.
        foreign: The fund's foreign-exposure percentage, or ``None`` if unknown.

    Returns:
        ``(israel_equity_exposure, israel_equity_share)`` where the first item is
        a percentage of the fund's assets and the second is the Israeli
        percentage of the fund's equity component. Either is ``None`` when it
        cannot be derived (missing data, or a fund with no equity for the share).
    """
    if equity is None or foreign is None:
        return None, None
    israel = min(max(equity - foreign, 0.0), max(equity, 0.0))
    share = israel / equity * 100 if equity > 0 else None
    return round(israel, 2), round(share, 1) if share is not None else None


class RiskClassifier:
    """Looks up a fund's equity exposure and derives a risk-level label.

    Risk bands:
    * ``"low"``    — equity exposure <= low_exposure_threshold
    * ``"medium"`` — equity exposure <= medium_exposure_threshold
    * ``"high"``   — equity exposure > medium_exposure_threshold
    * ``"invalid"`` — fund ID not found in the risk map
    """

    def __init__(
        self,
        risks: dict[int, float] | None = None,
        path: Path | None = None,
        foreign: dict[int, float] | None = None,
    ) -> None:
        """Construct a classifier from an in-memory map or an XML file.

        Args:
            risks: A pre-built fund-ID to equity-exposure mapping.
            path: Filesystem path to the risks-map XML file, used to build
                the equity and foreign mappings when *risks* is not provided.
            foreign: A pre-built fund-ID to foreign-exposure mapping, used
                alongside *risks*.

        Raises:
            ValueError: If neither *risks* nor *path* is given.
        """
        if risks is not None:
            self._risks = dict(risks)
            self._foreign = dict(foreign or {})
        elif path is not None:
            from src.parsers.risk_map_parser import parse_exposure_maps
            self._risks, self._foreign = parse_exposure_maps(path)
        else:
            raise ValueError("RiskClassifier requires either 'risks' or 'path'")

    def get_equity_exposure(self, fund_id: int) -> float | None:
        """Return the raw equity-exposure percentage for a fund, or None if unknown."""
        return self._risks.get(fund_id)

    def get_foreign_exposure(self, fund_id: int) -> float | None:
        """Return the raw foreign-exposure percentage for a fund, or None if unknown."""
        return self._foreign.get(fund_id)

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
