from typing import List

# בג apollo2 % python3 -m src.api.app
import uvicorn
from fastapi import FastAPI, Form, UploadFile, File
from src.engines.engine import run_comparison
from fastapi.middleware.cors import CORSMiddleware

APP = FastAPI()


APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@APP.post("/compare")
async def compare(
    weight_1: int = Form(),
    weight_3: int = Form(),
    weight_5: int = Form(),
    weight_sharp: int = Form(),
    mislaka_file: List[UploadFile] = File(...),
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
    uvicorn.run("src.api.app:APP", host="127.0.0.1", port=8000, reload=True)
