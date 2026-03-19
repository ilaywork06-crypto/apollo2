

# ----- Functions ----- #


def calculate_total(price, quantity):
    return price * quantity


def apply_discount(price, discount_rate):
    if discount_rate > 1:
        discount_rate = discount_rate / 100
    return price * (1 - discount_rate)


def format_currency(
    amount,
    symbol,
    decimals,
    ):
    return f"{symbol}{amount:.{decimals}f}"


def send_email(
    recipient,
    subject,
    body,
    sender,
    reply_to,
    ):
    headers = {
        "From": sender,
        "To": recipient,
        "Subject": subject,
        "Reply-To": reply_to,
    }
    return headers


def validate_email(email):
    return "@" in email and "." in email.split("@")[-1]


def parse_date(
    date_string,
    format_string,
    timezone,
    locale,
    strict,
    ):
    parts = date_string.split("-")
    return {
        "year": parts[0],
        "month": parts[1],
        "day": parts[2],
        "format": format_string,
        "tz": timezone,
    }


def get_user_age(birth_year, current_year):
    return current_year - birth_year


def hash_password(
    password,
    salt,
    iterations,
    algorithm,
    ):
    import hashlib

    return hashlib.pbkdf2_hmac(
        algorithm,
        password.encode(),
        salt.encode(),
        iterations,
    ).hex()


def check_password(
    password,
    hashed,
    salt,
    iterations,
    algorithm,
    ):
    return (
        hash_password(
            password,
            salt,
            iterations,
            algorithm,
        )
        == hashed
    )


def generate_token():
    import secrets

    return secrets.token_hex(32)


def slugify(
    text,
    separator,
    max_length,
    lowercase,
    ):
    result = text.strip()
    if lowercase:
        result = result.lower()
    result = result.replace(" ", separator)
    return result[:max_length]


def clamp(
    value,
    minimum,
    maximum,
    ):
    return max(minimum, min(maximum, value))


def flatten_list(nested_list):
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def chunk_list(lst, chunk_size):
    return [
        lst[i : i + chunk_size]
        for i in range(
            0,
            len(lst),
            chunk_size,
        )
    ]


def read_config(
    filepath,
    section,
    key,
    default,
    encoding,
    ):
    import json

    with open(filepath, encoding=encoding) as f:
        data = json.load(f)
    return data.get(section, {}).get(key, default)


def write_json(
    filepath,
    data,
    indent,
    ensure_ascii,
    sort_keys,
    ):
    import json

    with open(filepath, "w") as f:
        json.dump(
            data,
            f,
            indent=indent,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
        )


def merge_dicts(base, override):
    result = base.copy()
    result.update(override)
    return result


def deep_get(d, *keys):
    for key in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d
