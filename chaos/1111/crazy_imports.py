# ----- Imports ----- #

import os
import json
from pydantic import BaseModel
import hashlib
from urllib.parse import urlencode, urlparse
import csv
import io
from typing import Any
import uuid
import time
import logging
from functools import wraps
import itertools
from dataclasses import dataclass, field
import base64
import hmac


# ----- Classes ----- #


class AppConfig(BaseModel):
    host: str
    port: int
    debug: bool


@dataclass
class RequestContext:
    request_id: str = field(default_factory=generate_request_id)
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ----- Functions ----- #


def get_environment():
    return os.environ.copy()


def read_json_file(filepath):
    with open(filepath) as f:
        return json.load(f)


def build_query_string(params):
    return urlencode(params)


def parse_url(raw_url):
    return urlparse(raw_url)


def write_csv(rows, fieldnames):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def generate_request_id():
    return str(uuid.uuid4())


def timed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logging.debug(f"{func.__name__} took {elapsed:.3f}s")
        return result

    return wrapper


def chunk_iterable(iterable, size):
    it = iter(iterable)
    return iter(lambda: list(itertools.islice(it, size)), [])


def sign_payload(payload, secret):
    h = hmac.new(
        secret.encode(),
        json.dumps(payload).encode(),
        hashlib.sha256,
        )
    return base64.b64encode(h.digest()).decode()
