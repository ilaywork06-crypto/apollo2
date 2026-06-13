"""Community profile and leaderboard endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_profile_repository
from src.api.schemas import JoinRequest
from src.community.repository import ProfileRepository
from src.community.service import get_leaderboard, get_profile, join_community

router = APIRouter(prefix="/community")


@router.post("/join")
async def community_join(
    body: JoinRequest, repo: ProfileRepository = Depends(get_profile_repository)
) -> dict:
    funds = [f.model_dump() for f in body.funds]
    return await join_community(repo, body.client_id, funds)


@router.get("/leaderboard")
async def community_leaderboard(
    repo: ProfileRepository = Depends(get_profile_repository),
) -> dict:
    return await get_leaderboard(repo)


@router.get("/profile/{fake_name}")
async def community_profile(
    fake_name: str, repo: ProfileRepository = Depends(get_profile_repository)
) -> dict:
    profile = await get_profile(repo, fake_name)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
