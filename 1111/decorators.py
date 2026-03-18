# ----- Imports ----- #

import functools
import time
import logging


# ----- Other ----- #


logger = logging.getLogger(__name__)


# ----- Classes ----- #


class cache_result:
    def __init__(self, ttl_seconds):
        self.ttl = ttl_seconds
        self._cache = {}

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args):
            key = args
            cached = self._cache.get(key)
            if cached:
                value, ts = cached
                if time.time() - ts < self.ttl:
                    return value
            result = func(*args)
            self._cache[key] = (result, time.time())
            return result

        return wrapper


class ServiceClient:
    @staticmethod
    def from_env():
        import os

        return ServiceClient(
            os.getenv("SERVICE_URL", "http://localhost:8000"), os.getenv("SERVICE_TOKEN", "")
        )

    @retry(max_attempts=3, delay_seconds=0.5)
    @log_calls
    def call(
        self,
        method,
        path,
        payload,
        ):
        return {"method": method, "path": path, "payload": payload}

    def __init__(
        self,
        base_url,
        token,
        ):
        self.base_url = base_url
        self.token = token


class DataPipeline:
    def __init__(self, name):
        self.name = name
        self.steps = []

    @log_calls
    def run(self, data):
        for step in self.steps:
            data = step(data)
        return data

    def add_step(self, func):
        self.steps.append(func)
        return self


# ----- Functions ----- #


def retry(max_attempts, delay_seconds):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay_seconds)

        return wrapper

    return decorator


def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} returned")
        return result

    return wrapper


def require_auth(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        token = kwargs.get("token") or (args[0] if args else None)
        if not token:
            raise PermissionError("Authentication required")
        return func(*args, **kwargs)

    return wrapper


@retry(max_attempts=3, delay_seconds=1)
def fetch_remote_data(url, timeout):
    import urllib.request

    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


@log_calls
def process_invoice(
    invoice_id,
    amount,
    currency,
    ):
    return {"id": invoice_id, "amount": amount, "currency": currency, "status": "processed"}


@require_auth
@log_calls
def get_sensitive_data(token, resource_id):
    return {"resource": resource_id, "data": "classified", "accessed_by": token[:8]}


@cache_result(ttl_seconds=60)
def get_exchange_rate(from_currency, to_currency):
    rates = {"USD_EUR": 0.92, "USD_GBP": 0.79, "EUR_GBP": 0.86}
    return rates.get(f"{from_currency}_{to_currency}", 1.0)


@retry(max_attempts=2, delay_seconds=0.5)
@log_calls
def send_webhook(
    endpoint,
    payload,
    secret,
    ):
    import json, hmac, hashlib

    body = json.dumps(payload).encode()
    sig = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return {"endpoint": endpoint, "signature": sig, "delivered": True}
