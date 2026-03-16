import uvicorn
from fastapi import FastAPI, Form, UploadFile, File
from src.engines.engine import run_comparison
APP = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
@APP.post("/compare")
async def compare(
    weight_1:int = Form(),
    weight_3:int  = Form(), 
    weight_5:int = Form(),
    weight_sharp:int = Form(),
    mislaka_file: UploadFile = File(...),
    ):
    mislaka_content = (await mislaka_file.read()).decode('utf-8-sig')
    content = run_comparison(mislaka_file=mislaka_content, weight_1 = weight_1, weight_3 = weight_3, weight_5 = weight_5, weight_sharp = weight_sharp)
    return content

@APP.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("src.api.app:APP", host="127.0.0.1", port=8000, reload=True)