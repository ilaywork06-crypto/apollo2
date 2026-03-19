# ----- Imports ----- #

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import os
from fastapi.middleware.cors import CORSMiddleware
import logging

# ----- Constants ----- #

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inventory.db")
DEFAULT_PAGE_SIZE = 20
NEXT_ID = 1


# ----- Other ----- #


app = FastAPI(title="Inventory API")
MAX_ITEMS_PER_PAGE = 100
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    )
logger = logging.getLogger(__name__)
ITEMS_DB: list[dict] = []
USERS_DB: list[dict] = []


# ----- Classes ----- #


class ItemCreate(BaseModel):
    name: str
    sku: str
    price: float
    stock: int
    category: str


class ItemResponse(BaseModel):
    id: int
    name: str
    sku: str
    price: float
    stock: int
    category: str


class UserCreate(BaseModel):
    username: str
    email: str
    role: str


# ----- Functions ----- #


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    )
def create_item(item: ItemCreate):
    global NEXT_ID
    record = {
        "id": NEXT_ID,
        "name": item.name,
        "sku": item.sku,
        "price": item.price,
        "stock": item.stock,
        "category": item.category,
    }
    ITEMS_DB.append(record)
    NEXT_ID += 1
    return record


@app.get("/items", response_model=list[ItemResponse])
def list_items(
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    category: str | None = None,
    ):
    results = ITEMS_DB
    if category:
        results = [i for i in results if i["category"] == category]
    start = (page - 1) * min(page_size, MAX_ITEMS_PER_PAGE)
    return results[start : start + page_size]


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    for item in ITEMS_DB:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item: ItemCreate):
    for idx, existing in enumerate(ITEMS_DB):
        if existing["id"] == item_id:
            ITEMS_DB[idx] = {
                "id": item_id,
                "name": item.name,
                "sku": item.sku,
                "price": item.price,
                "stock": item.stock,
                "category": item.category,
            }
            return ITEMS_DB[idx]
    raise HTTPException(status_code=404, detail="Item not found")


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    global ITEMS_DB
    original_len = len(ITEMS_DB)
    ITEMS_DB = [i for i in ITEMS_DB if i["id"] != item_id]
    if len(ITEMS_DB) == original_len:
        raise HTTPException(status_code=404, detail="Item not found")


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    record = {
        "id": len(USERS_DB) + 1,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }
    USERS_DB.append(record)
    return record


@app.get("/users")
def list_users():
    return USERS_DB


@app.get("/stats")
def get_stats():
    total_value = sum(i["price"] * i["stock"] for i in ITEMS_DB)
    return {
        "total_items": len(ITEMS_DB),
        "total_users": len(USERS_DB),
        "inventory_value": total_value,
    }
