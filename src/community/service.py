"""Community service: orchestrates profile creation, leaderboard, and profile lookup."""

from src.community.aggregation import (
    apply_percentages,
    build_profile_payload,
    dominant_risk,
    to_funds_json,
    to_leaderboard_row,
    to_profile_dict,
    today_str,
    weighted_equity_exposure,
    weighted_score,
    weighted_tsua,
)
from src.community.hashing import hash_client_id
from src.community.repository import ProfileRepository


async def join_community(repo: ProfileRepository, client_id: str, funds: list[dict]) -> dict:
    """Create or update a community profile for *client_id* and return its public payload.

    Args:
        repo: Repository used to persist the profile.
        client_id: The client's raw identifier (hashed before storage).
        funds: The client's funds, each with ``"amount"``, ``"tsua_1"``,
            ``"grade"``, ``"risk_level"``, and ``"equity_exposure"`` keys.

    Returns:
        ``{"success": True, "profile": {...}}`` with the computed profile.
    """
    client_hash = hash_client_id(client_id)
    funds_with_pct = apply_percentages(funds)

    profile_weighted_tsua = weighted_tsua(funds_with_pct)
    profile_weighted_score = weighted_score(funds_with_pct)
    profile_weighted_equity_exposure = weighted_equity_exposure(funds_with_pct)
    profile_dominant_risk = dominant_risk(funds_with_pct)
    funds_json = to_funds_json(funds_with_pct)
    joined = today_str()

    fake_name = await repo.save_profile(
        client_hash,
        profile_weighted_tsua,
        profile_weighted_score,
        profile_dominant_risk,
        profile_weighted_equity_exposure,
        joined,
        funds_json,
    )

    return {
        "success": True,
        "profile": build_profile_payload(
            fake_name,
            profile_weighted_tsua,
            profile_weighted_score,
            profile_dominant_risk,
            profile_weighted_equity_exposure,
            funds_json,
            joined,
        ),
    }


async def get_leaderboard(repo: ProfileRepository) -> dict:
    """Return all community profiles sorted by weighted score descending."""
    rows = await repo.fetch_leaderboard()
    return {"profiles": [to_leaderboard_row(row) for row in rows]}


async def get_profile(repo: ProfileRepository, fake_name: str) -> dict | None:
    """Return full profile details for *fake_name*, or ``None`` if not found."""
    row = await repo.fetch_profile(fake_name)
    if row is None:
        return None
    return to_profile_dict(row)
