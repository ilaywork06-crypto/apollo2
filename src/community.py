"""Community feature: anonymous investor profiles and leaderboard."""

import hashlib
import json
import random
from datetime import date

import asyncpg

ANIMALS = [
    "נשר", "דולפין", "אריה", "פנתר", "זאב", "נמר", "עיט", "ינשוף",
    "שועל", "דרקון", "נץ", "פלמינגו", "דוב", "טיגריס", "חתול",
]


async def init_db(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                client_id_hash           TEXT PRIMARY KEY,
                fake_name                TEXT UNIQUE NOT NULL,
                weighted_tsua            DOUBLE PRECISION,
                weighted_score           DOUBLE PRECISION,
                dominant_risk            TEXT,
                weighted_equity_exposure DOUBLE PRECISION,
                joined                   TEXT,
                funds                    JSONB NOT NULL DEFAULT '[]'::jsonb
            )
        """)


def _hash_client_id(client_id: str) -> str:
    return hashlib.sha256(client_id.encode()).hexdigest()


async def _generate_fake_name(conn: asyncpg.Connection) -> str:
    rows = await conn.fetch("SELECT fake_name FROM profiles")
    existing = {row["fake_name"] for row in rows}
    for _ in range(200):
        name = f"{random.choice(ANIMALS)} {random.randint(10, 99)}"
        if name not in existing:
            return name
    return f"{random.choice(ANIMALS)} {random.randint(10, 99)}"


async def join_community(pool: asyncpg.Pool, client_id: str, funds: list[dict]) -> dict:
    """Create or update a community profile."""
    client_hash = _hash_client_id(client_id)

    total_amount = sum(f.get("amount", 0) for f in funds)
    if total_amount == 0:
        total_amount = 1

    funds_with_pct = []
    for f in funds:
        pct = round(f.get("amount", 0) / total_amount * 100, 1)
        funds_with_pct.append({**f, "pct_of_total": pct})

    weighted_tsua = sum(f["tsua_1"] * f["pct_of_total"] / 100 for f in funds_with_pct)

    weighted_score = sum(
        f.get("grade", 0) * f["pct_of_total"] / 100
        for f in funds_with_pct
        if f.get("grade", 0) > 0
    )

    funds_with_exposure = [f for f in funds_with_pct if f.get("equity_exposure") is not None]
    if funds_with_exposure:
        exposure_weight_total = sum(f["pct_of_total"] for f in funds_with_exposure)
        weighted_equity_exposure = (
            sum(f["equity_exposure"] * f["pct_of_total"] for f in funds_with_exposure)
            / exposure_weight_total
            if exposure_weight_total > 0 else None
        )
    else:
        weighted_equity_exposure = None

    risk_pct: dict[str, float] = {}
    for f in funds_with_pct:
        risk = f.get("risk_level", "high")
        risk_pct[risk] = risk_pct.get(risk, 0.0) + f["pct_of_total"]
    dominant_risk = max(risk_pct, key=risk_pct.get) if risk_pct else "high"

    today = date.today().strftime("%d/%m/%Y")
    funds_json = [{"name": f["name"], "id": f["id"], "pct": f["pct_of_total"]} for f in funds_with_pct]

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT fake_name FROM profiles WHERE client_id_hash = $1", client_hash
        )
        fake_name = existing["fake_name"] if existing else await _generate_fake_name(conn)

        await conn.execute("""
            INSERT INTO profiles (
                client_id_hash, fake_name, weighted_tsua, weighted_score,
                dominant_risk, weighted_equity_exposure, joined, funds
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (client_id_hash) DO UPDATE SET
                weighted_tsua            = EXCLUDED.weighted_tsua,
                weighted_score           = EXCLUDED.weighted_score,
                dominant_risk            = EXCLUDED.dominant_risk,
                weighted_equity_exposure = EXCLUDED.weighted_equity_exposure,
                joined                   = EXCLUDED.joined,
                funds                    = EXCLUDED.funds
        """,
            client_hash, fake_name,
            round(weighted_tsua, 2), round(weighted_score, 2),
            dominant_risk, round(weighted_equity_exposure, 1) if weighted_equity_exposure is not None else None,
            today, json.dumps(funds_json),
        )

    return {
        "success": True,
        "profile": {
            "fake_name": fake_name,
            "weighted_tsua": round(weighted_tsua, 2),
            "weighted_score": round(weighted_score, 2),
            "dominant_risk": dominant_risk,
            "weighted_equity_exposure": round(weighted_equity_exposure, 1) if weighted_equity_exposure is not None else None,
            "funds": funds_json,
            "joined": today,
        },
    }


async def get_leaderboard(pool: asyncpg.Pool) -> dict:
    """Return all profiles sorted by weighted_score descending."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT fake_name, weighted_tsua, weighted_score, dominant_risk,
                   weighted_equity_exposure, funds, joined
            FROM profiles
            ORDER BY weighted_score DESC
        """)

    result = []
    for row in rows:
        joined_full = row["joined"] or ""
        try:
            parts = joined_full.split("/")
            joined_short = f"{parts[1]}/{parts[2]}" if len(parts) == 3 else joined_full
        except Exception:
            joined_short = joined_full
        funds = json.loads(row["funds"]) if isinstance(row["funds"], str) else (row["funds"] or [])
        result.append({
            "fake_name": row["fake_name"],
            "weighted_tsua": row["weighted_tsua"],
            "weighted_score": row["weighted_score"],
            "dominant_risk": row["dominant_risk"],
            "weighted_equity_exposure": row["weighted_equity_exposure"],
            "num_funds": len(funds),
            "joined": joined_short,
        })
    return {"profiles": result}


async def get_profile(pool: asyncpg.Pool, fake_name: str) -> dict | None:
    """Return full profile details for a given fake_name, or None if not found."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT fake_name, weighted_tsua, weighted_score, dominant_risk,
                   weighted_equity_exposure, joined, funds
            FROM profiles
            WHERE fake_name = $1
        """, fake_name)

    if row is None:
        return None

    funds = json.loads(row["funds"]) if isinstance(row["funds"], str) else (row["funds"] or [])
    return {
        "fake_name": row["fake_name"],
        "weighted_tsua": row["weighted_tsua"],
        "weighted_score": row["weighted_score"],
        "dominant_risk": row["dominant_risk"],
        "weighted_equity_exposure": row["weighted_equity_exposure"],
        "joined": row["joined"],
        "funds": funds,
    }
