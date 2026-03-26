"""FastAPI application entry point for the Apollo fund comparison service."""

# ----- Imports ----- #

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# כל הקופות נתותים כללים לשנה וחלוקה לקבוצות ראשיות לחודש ב15 לחודש?
# בג apollo2 % python3 -m src.api.app
import uvicorn
from pydantic import BaseModel

from src.community import get_leaderboard, get_profile, join_community
from src.core.engine import run_comparison


# ----- Community request models ----- #


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


APP = FastAPI()


APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Functions ----- #


@APP.post("/compare")
async def compare(
    weight_1: int = Form(),
    weight_3: int = Form(),
    weight_5: int = Form(),
    low_exposure_threshold: int = Form(),
    medium_exposure_threshold: int = Form(),
    weight_sharp: int = Form(),
    mislaka_file: list[UploadFile] = File(...),
    bad_hevrot: list[str] = Form([]),
) -> dict:
    """Run a fund comparison based on uploaded Mislaka files and user-supplied weights.

    Args:
        weight_1: Weight applied to the 1-year cumulative return metric.
        weight_3: Weight applied to the 3-year average annual return metric.
        weight_5: Weight applied to the 5-year average annual return metric.
        weight_sharp: Weight applied to the Sharpe ratio metric.
        mislaka_file: One or more Mislaka XML files uploaded by the client.

    Returns:
        A dict containing a ``funds`` key with the ranked comparison results.
    """
    l_con = []
    for file in mislaka_file:
        mislaka_content = (await file.read()).decode("utf-8-sig")
        l_con.append(mislaka_content)
    content = run_comparison(
        mislaka_file=l_con,
        weight_1=weight_1,
        weight_3=weight_3,
        weight_5=weight_5,
        weight_sharp=weight_sharp,
        low_exposure_threshold=low_exposure_threshold,
        medium_exposure_threshold=medium_exposure_threshold,
        bad_hevrot=bad_hevrot,
    )
    return content


@APP.post("/community/join")
async def community_join(body: JoinRequest) -> dict:
    """Create or update an anonymous community profile for the given client."""
    funds = [f.model_dump() for f in body.funds]
    return join_community(body.client_id, funds)


@APP.get("/community/leaderboard")
async def community_leaderboard() -> dict:
    """Return all community profiles sorted by score."""
    return get_leaderboard()


@APP.get("/community/profile/{fake_name}")
async def community_profile(fake_name: str) -> dict:
    """Return full profile details for the given fake_name."""
    profile = get_profile(fake_name)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@APP.get("/health")
async def health() -> dict:
    """Return a simple health-check response indicating the service is running.

    Returns:
        A dict with a ``status`` key set to ``"ok"``.
    """
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:APP",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
