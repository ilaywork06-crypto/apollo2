"""Fund comparison endpoint."""

from fastapi import APIRouter, File, Form, UploadFile

from src.comparison.service import run_comparison

router = APIRouter()


@router.post("/compare")
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
