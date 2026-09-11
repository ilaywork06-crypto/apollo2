"""Pydantic request models for the API."""

from pydantic import BaseModel


class FundInput(BaseModel):
    name: str
    id: str
    risk_level: str
    tsua_1: float
    grade: float
    amount: float
    pct_of_total: float = 0.0
    equity_exposure: float | None = None


class JoinRequest(BaseModel):
    client_id: str
    funds: list[FundInput]


class BulkComparisonParams(BaseModel):
    """Scalar form fields of a bulk comparison (the files are read separately)."""

    weight_1: int
    weight_3: int
    weight_5: int
    weight_sharp: int
    weight_liquidity: int = 0
    low_exposure_threshold: int
    medium_exposure_threshold: int
    bad_hevrot: list[str] = []
    override_risk_level: str | None = None
    israel_share_min: float = 0.0
    israel_share_max: float = 100.0
