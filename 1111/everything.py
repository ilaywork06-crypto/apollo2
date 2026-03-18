# ----- Imports ----- #

import os
import json
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import logging
from fastapi.middleware.cors import CORSMiddleware
import re
import hmac as hmac_module
import base64
from datetime import datetime, UTC
import time
from functools import wraps
import csv
import io
import threading

# ----- Constants ----- #

HASH_ALGORITHM = "sha256"
DEFAULT_PAGE = 1
APP_VERSION = "2.1.0"
DEBUG_MODE = True
RATE_LIMIT = 100

# ----- Other ----- #


INVENTORY: list[ProductInventory] = []
REPORT_REGISTRY: dict[str, ReportEngine] = {}
TOKEN_EXPIRY_SECONDS = 86400
USERS_STORE: dict[str, dict] = {}
DEFAULT_PAGE_SIZE = 25
MAX_CONNECTIONS = 50
SESSIONS_STORE: dict[str, dict] = {}
MAX_PAGE_SIZE = 200
app = FastAPI(title="Chaos App", version=APP_VERSION)
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
audit = AuditLogger(
    "chaos-app",
    "INFO",
    "/var/log/app.log",
    True,
    100,
    True,
)
_lock = threading.Lock()

# ----- Classes ----- #


class UserCredentials(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class AuditLogger:
    def __init__(
        self,
        service_name,
        log_level,
        output_file,
        rotate_daily,
        max_size_mb,
        include_request_id,
        ):
        self.service = service_name
        self.level = log_level
        self.output = output_file
        self.rotate = rotate_daily
        self.max_size = max_size_mb
        self.include_id = include_request_id
        self._entries = []

    def log(
        self,
        event,
        user,
        resource,
        action,
        outcome,
        ):
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "event": event,
            "user": user,
            "resource": resource,
            "action": action,
            "outcome": outcome,
        }
        self._entries.append(entry)
        return entry

    def flush(self):
        count = len(self._entries)
        self._entries.clear()
        return count


class ProductInventory:
    def __init__(
        self,
        product_id,
        name,
        sku,
        price,
        stock,
        category,
        supplier,
        warehouse_id,
        ):
        self.product_id = product_id
        self.name = name
        self.sku = sku
        self.price = price
        self.stock = stock
        self.category = category
        self.supplier = supplier
        self.warehouse_id = warehouse_id

    def reserve(self, qty):
        if qty > self.stock:
            raise ValueError(f"Insufficient stock: {self.stock} < {qty}")
        self.stock -= qty
        return {"reserved": qty, "remaining": self.stock}

    def to_dict(self):
        return {
            "id": self.product_id,
            "name": self.name,
            "sku": self.sku,
            "price": self.price,
            "stock": self.stock,
        }


class ReportEngine:
    def __init__(
        self,
        title,
        owner,
        recipients,
        schedule,
        format_type,
        include_summary,
        max_rows,
        timezone_name,
        ):
        self.title = title
        self.owner = owner
        self.recipients = recipients
        self.schedule = schedule
        self.format_type = format_type
        self.include_summary = include_summary
        self.max_rows = max_rows
        self.tz = timezone_name

    def generate(self):
        data = paginate_and_sort(
            INVENTORY,
            1,
            self.max_rows,
            "name",
            False,
            lambda x: True,
            lambda x: x.to_dict(),
        )
        summary = (
            {"total": len(INVENTORY), "categories": len(set(p.category for p in INVENTORY))}
            if self.include_summary
            else {}
        )
        return {"title": self.title, "data": data, "summary": summary}

# ----- Functions ----- #


def normalize_text(
    text,
    strip_html,
    lowercase,
    max_length,
    encoding,
    preserve_newlines,
    ):
    if strip_html:
        text = re.sub(
            r"<[^>]+>",
            "",
            text,
        )
    if lowercase:
        text = text.lower()
    if max_length:
        text = text[:max_length]
    return text.encode(encoding).decode(encoding)


def generate_token(
    user_id,
    secret,
    expiry,
    algorithm,
    include_metadata,
    metadata,
    ):
    payload = {"sub": user_id, "exp": expiry, "meta": metadata if include_metadata else {}}
    raw = json.dumps(payload, sort_keys=True).encode()
    sig = hmac_module.new(
        secret.encode(),
        raw,
        algorithm,
    ).hexdigest()
    return base64.urlsafe_b64encode(f"{raw.decode()}:{sig}".encode()).decode()


def timed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.time()
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} took {time.time() - t0:.3f}s")
        return result

    return wrapper


def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = kwargs.get("token")
        if not token or token not in SESSIONS_STORE:
            raise PermissionError("Unauthorized")
        return func(*args, **kwargs)

    return wrapper


def paginate_and_sort(
    items,
    page,
    page_size,
    sort_key,
    reverse,
    filter_fn,
    transform_fn,
    ):
    filtered = [transform_fn(item) for item in items if filter_fn(item)]
    filtered.sort(key=lambda x: x.get(sort_key), reverse=reverse)
    start = (page - 1) * min(page_size, MAX_PAGE_SIZE)
    return filtered[start : start + page_size]


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION, "debug": DEBUG_MODE}


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserCredentials):
    user = USERS_STORE.get(credentials.username)
    if not user or user["password"] != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = generate_token(
        credentials.username,
        os.getenv("SECRET", "dev"),
        TOKEN_EXPIRY_SECONDS,
        HASH_ALGORITHM,
        True,
        {"login_time": time.time()},
    )
    SESSIONS_STORE[token] = {"user": credentials.username, "created": time.time()}
    audit.log(
        "login",
        credentials.username,
        "auth",
        "login",
        "success",
    )
    return {"access_token": token, "token_type": "bearer", "expires_in": TOKEN_EXPIRY_SECONDS}


@app.get("/inventory")
@timed
def list_inventory(
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    category: str | None = None,
    min_stock: int = 0,
    ):
    items = [
        p.to_dict()
        for p in INVENTORY
        if (category is None or p.category == category) and p.stock >= min_stock
    ]
    start = (page - 1) * min(page_size, MAX_PAGE_SIZE)
    return {"items": items[start : start + page_size], "total": len(items), "page": page}


@app.post("/inventory", status_code=status.HTTP_201_CREATED)
def add_product(
    product_id: str,
    name: str,
    sku: str,
    price: float,
    stock: int,
    category: str,
    supplier: str,
    warehouse_id: str,
    ):
    p = ProductInventory(
        product_id,
        name,
        sku,
        price,
        stock,
        category,
        supplier,
        warehouse_id,
    )
    INVENTORY.append(p)
    return p.to_dict()


def export_inventory_csv(
    include_price,
    include_stock,
    delimiter,
    encoding,
    sort_by,
    filter_category,
    ):
    fields = ["id", "name", "sku"]
    if include_price:
        fields.append("price")
    if include_stock:
        fields.append("stock")
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        delimiter=delimiter,
        extrasaction="ignore",
    )
    writer.writeheader()
    items = [p.to_dict() for p in INVENTORY if not filter_category or p.category == filter_category]
    items.sort(key=lambda x: x.get(sort_by, ""))
    writer.writerows(items)
    return output.getvalue().encode(encoding)


@app.get("/reports/{report_id}")
def run_report(report_id: str):
    engine = REPORT_REGISTRY.get(report_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Report not found")
    return engine.generate()


def atomic_reserve(
    product_id,
    quantity,
    requester_id,
    order_id,
    priority,
    fallback_warehouse,
    ):
    with _lock:
        for p in INVENTORY:
            if p.product_id == product_id:
                result = p.reserve(quantity)
                audit.log(
                    "reserve",
                    requester_id,
                    product_id,
                    "reserve",
                    "success",
                )
                return {**result, "order": order_id, "priority": priority}
    raise HTTPException(status_code=404, detail="Product not found")
