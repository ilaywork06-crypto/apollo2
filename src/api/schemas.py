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
