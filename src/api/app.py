"""FastAPI application entry point for the Apollo fund comparison service."""

# ----- Imports ----- #

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# כל הקופות נתותים כללים לשנה וחלוקה לקבוצות ראשיות לחודש ב15 לחודש?
# בג apollo2 % python3 -m src.api.app
import uvicorn

from src.core.engine import run_comparison


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
    )
    return content


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
