"""Database access for community profiles, backed by an asyncpg connection pool."""

import json

import asyncpg

from src.community.naming import generate_fake_name

_CREATE_TABLE_SQL = """
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
"""

_SELECT_FAKE_NAME_BY_HASH_SQL = "SELECT fake_name FROM profiles WHERE client_id_hash = $1"

_SELECT_ALL_FAKE_NAMES_SQL = "SELECT fake_name FROM profiles"

_UPSERT_PROFILE_SQL = """
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
"""

_SELECT_LEADERBOARD_SQL = """
    SELECT fake_name, weighted_tsua, weighted_score, dominant_risk,
           weighted_equity_exposure, funds, joined
    FROM profiles
    ORDER BY weighted_score DESC
"""

_SELECT_PROFILE_BY_FAKE_NAME_SQL = """
    SELECT fake_name, weighted_tsua, weighted_score, dominant_risk,
           weighted_equity_exposure, joined, funds
    FROM profiles
    WHERE fake_name = $1
"""


class ProfileRepository:
    """Wraps an asyncpg connection pool for all access to the ``profiles`` table."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def init_schema(self) -> None:
        """Create the ``profiles`` table if it doesn't already exist."""
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE_SQL)

    async def save_profile(
        self,
        client_id_hash: str,
        weighted_tsua: float,
        weighted_score: float,
        dominant_risk: str,
        weighted_equity_exposure: float | None,
        joined: str,
        funds_json: list[dict],
    ) -> str:
        """Insert or update a profile row and return its fake name.

        If a profile already exists for *client_id_hash*, its existing fake
        name is reused; otherwise a new, unused one is generated.

        Args:
            client_id_hash: The hashed client identifier (primary key).
            weighted_tsua: Percentage-weighted average annual return.
            weighted_score: Percentage-weighted average grade.
            dominant_risk: The client's dominant risk level.
            weighted_equity_exposure: Percentage-weighted average equity
                exposure, or ``None``.
            joined: The join/update date as ``DD/MM/YYYY``.
            funds_json: The client's funds, projected to public fields.

        Returns:
            The profile's fake name (existing or newly generated).
        """
        async with self._pool.acquire() as conn:
            existing = await conn.fetchrow(_SELECT_FAKE_NAME_BY_HASH_SQL, client_id_hash)
            if existing:
                fake_name = existing["fake_name"]
            else:
                rows = await conn.fetch(_SELECT_ALL_FAKE_NAMES_SQL)
                fake_name = generate_fake_name({row["fake_name"] for row in rows})

            await conn.execute(
                _UPSERT_PROFILE_SQL,
                client_id_hash,
                fake_name,
                round(weighted_tsua, 2),
                round(weighted_score, 2),
                dominant_risk,
                round(weighted_equity_exposure, 1) if weighted_equity_exposure is not None else None,
                joined,
                json.dumps(funds_json),
            )
        return fake_name

    async def fetch_leaderboard(self) -> list:
        """Return all profile rows, ordered by ``weighted_score`` descending."""
        async with self._pool.acquire() as conn:
            return await conn.fetch(_SELECT_LEADERBOARD_SQL)

    async def fetch_profile(self, fake_name: str):
        """Return the profile row for *fake_name*, or ``None`` if not found."""
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(_SELECT_PROFILE_BY_FAKE_NAME_SQL, fake_name)
