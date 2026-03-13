import uvicorn
from fastapi import FastAPI, UploadFile, File
from src.engines.engine import run_comparison
APP = FastAPI()

@APP.post("/compare")
async def compare(
    mislaka_file: UploadFile = File(...),
    gemelnet_file: UploadFile = File(...)
    ):
    mislaka_content = (await mislaka_file.read()).decode('utf-8-sig')
    gemelnet_content = (await gemelnet_file.read()).decode('utf-8-sig')
    content = run_comparison(gemel_net_file=gemelnet_content,mislaka_file=mislaka_content)
    return content

@APP.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("src.api.app:APP", host="127.0.0.1", port=8000, reload=True)