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
    weight_sharp: int = Form(),
    mislaka_file: list[UploadFile] = File(...),
    ):
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
    )
    return content


@APP.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:APP",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
