

# ----- Classes ----- #


class UserAccount:
    def __init__(
        self,
        username,
        email,
        password_hash,
        created_at,
        is_active,
        ):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.is_active = is_active

    def deactivate(self):
        self.is_active = False

    def to_dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "active": self.is_active,
        }


class ProductCatalog:
    def __init__(
        self,
        name,
        sku,
        price,
        stock_count,
        category,
        supplier_id,
        ):
        self.name = name
        self.sku = sku
        self.price = price
        self.stock_count = stock_count
        self.category = category
        self.supplier_id = supplier_id

    def is_available(self):
        return self.stock_count > 0

    def apply_discount(self, rate):
        self.price = self.price * (1 - rate)

    def restock(self, quantity):
        self.stock_count += quantity


class OrderProcessor:
    def __init__(
        self,
        order_id,
        customer,
        items,
        shipping_address,
        payment_method,
        discount_code,
        ):
        self.order_id = order_id
        self.customer = customer
        self.items = items
        self.shipping_address = shipping_address
        self.payment_method = payment_method
        self.discount_code = discount_code
        self.status = "pending"

    def calculate_total(self):
        return sum(item["price"] * item["qty"] for item in self.items)

    def process(self):
        if not self.items:
            raise ValueError("No items in order")
        self.status = "processing"
        return self.calculate_total()

    def cancel(self, reason):
        self.status = "cancelled"
        return {"order": self.order_id, "reason": reason}


class EmailService:
    def __init__(
        self,
        host,
        port,
        username,
        password,
        ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def send(
        self,
        to,
        subject,
        body,
        ):
        return {"to": to, "subject": subject, "sent": True}

    def send_bulk(
        self,
        recipients,
        subject,
        body,
        batch_size,
        ):
        results = []
        for i in range(
            0,
            len(recipients),
            batch_size,
        ):
            batch = recipients[i : i + batch_size]
            for r in batch:
                results.append(
                    self.send(
                        r,
                        subject,
                        body,
                    )
                )
        return results


class CacheManager:
    def __init__(
        self,
        max_size,
        ttl_seconds,
        eviction_policy,
        ):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.policy = eviction_policy
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def set(
        self,
        key,
        value,
        ):
        if len(self._store) >= self.max_size:
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


class ReportGenerator:
    def __init__(
        self,
        title,
        author,
        date,
        format_type,
        include_charts,
        page_size,
        orientation,
        ):
        self.title = title
        self.author = author
        self.date = date
        self.format_type = format_type
        self.include_charts = include_charts
        self.page_size = page_size
        self.orientation = orientation
        self.sections = []

    def add_section(
        self,
        heading,
        content,
        ):
        self.sections.append({"heading": heading, "content": content})

    def render(self):
        return {
            "title": self.title,
            "sections": self.sections,
            "format": self.format_type,
        }


class DatabaseConnection:
    def __init__(
        self,
        host,
        port,
        database,
        user,
        password,
        ssl_mode,
        ):
        self.dsn = f"{user}:{password}@{host}:{port}/{database}?sslmode={ssl_mode}"
        self._connected = False

    def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def execute(
        self,
        query,
        params,
        ):
        if not self._connected:
            raise RuntimeError("Not connected")
        return {"query": query, "params": params, "rows": []}
