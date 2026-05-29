"""FastAPI application entry point for the Apollo fund comparison service."""

import os
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.community import get_leaderboard, get_profile, init_db, join_community
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


# ----- App lifecycle ----- #


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await asyncpg.create_pool(
        os.environ.get("DATABASE_URL", "postgresql://apollo:apollo@localhost:5432/apollo")
    )
    await init_db(pool)
    app.state.pool = pool
    yield
    await pool.close()


APP = FastAPI(lifespan=lifespan)

APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Dependencies ----- #


async def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


# ----- Routes ----- #


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
    override_risk_level: str | None = Form(None),
) -> dict:
    l_con = []
    for file in mislaka_file:
        mislaka_content = (await file.read()).decode("utf-8-sig")
        l_con.append(mislaka_content)
    return run_comparison(
        mislaka_file=l_con,
        weight_1=weight_1,
        weight_3=weight_3,
        weight_5=weight_5,
        weight_sharp=weight_sharp,
        low_exposure_threshold=low_exposure_threshold,
        medium_exposure_threshold=medium_exposure_threshold,
        bad_hevrot=bad_hevrot,
        override_risk_level=override_risk_level,
    )


@APP.post("/community/join")
async def community_join(body: JoinRequest, pool: asyncpg.Pool = Depends(get_pool)) -> dict:
    funds = [f.model_dump() for f in body.funds]
    return await join_community(pool, body.client_id, funds)


@APP.get("/community/leaderboard")
async def community_leaderboard(pool: asyncpg.Pool = Depends(get_pool)) -> dict:
    return await get_leaderboard(pool)


@APP.get("/community/profile/{fake_name}")
async def community_profile(fake_name: str, pool: asyncpg.Pool = Depends(get_pool)) -> dict:
    profile = await get_profile(pool, fake_name)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@APP.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("src.api.app:APP", host="127.0.0.1", port=8000, reload=True)
