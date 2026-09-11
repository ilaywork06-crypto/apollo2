"""Fund comparison endpoints."""

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.datastructures import UploadFile as StarletteUploadFile

from src.api.schemas import BulkComparisonParams
from src.comparison.service import run_bulk_comparison, run_comparison

router = APIRouter()

# Starlette caps a multipart form at 1000 files by default; a bulk run over a
# whole client base can exceed that.
MAX_BULK_FILES = 10_000


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
    weight_liquidity: int = Form(0),
    israel_share_min: float = Form(0.0),
    israel_share_max: float = Form(100.0),
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
        weight_liquidity=weight_liquidity,
        israel_share_min=israel_share_min,
        israel_share_max=israel_share_max,
    )


@router.post("/compare/bulk")
async def compare_bulk(request: Request) -> dict:
    """Rank many clients, whose Mislaka files are uploaded together, by urgency to move.

    Takes the same form fields as ``/compare``. The form is parsed here rather
    than declared as parameters so the upload isn't capped at Starlette's
    default file limit.
    """
    form = await request.form(max_files=MAX_BULK_FILES)
    fields = {key: value for key, value in form.items() if isinstance(value, str)}
    fields["bad_hevrot"] = [v for v in form.getlist("bad_hevrot") if isinstance(v, str)]
    try:
        params = BulkComparisonParams.model_validate(fields)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_url=False)) from exc

    uploads = [f for f in form.getlist("mislaka_file") if isinstance(f, StarletteUploadFile)]
    if not uploads:
        raise HTTPException(status_code=422, detail="No mislaka_file uploaded")
    files = []
    for upload in uploads:
        files.append((upload.filename or "", await upload.read()))
        await upload.close()
    return run_bulk_comparison(files, **params.model_dump())
