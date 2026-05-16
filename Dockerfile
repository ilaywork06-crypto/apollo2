FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    python-multipart \
    lxml

COPY src/ ./src/
COPY data/ ./data/

CMD ["uvicorn", "src.api.app:APP", "--host", "0.0.0.0", "--port", "8000", "--reload"]
