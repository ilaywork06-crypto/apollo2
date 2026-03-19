

# ----- Functions ----- #


def validate_age(age):
    if age < 0:
        raise ValueError("Age cannot be negative")
    if age > 150:
        raise ValueError("Age seems unrealistic")
    return True


def validate_name(name):

    if not name:
        raise ValueError("Name cannot be empty")

    if len(name) > 255:
        raise ValueError("Name too long")

    return name.strip()


def validate_email(email):
    if "@" not in email:
        return False
    local, _, domain = email.partition("@")
    return bool(local) and "." in domain


def parse_int(value, default):
    try:
        return int(value)

    except (TypeError, ValueError):
        return default


def parse_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_divide(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator


def clamp_value(
    value,
    lo,
    hi,
    ):

    return max(lo, min(hi, value))


def normalize_score(
    score,
    min_score,
    max_score,
    ):
    if max_score == min_score:
        return 0.0
    return (score - min_score) / (max_score - min_score)


def compute_stats(values):
    if not values:
        return {}
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    import math

    std_dev = math.sqrt(variance)

    sorted_vals = sorted(values)

    median = (
        sorted_vals[n // 2]
        if n % 2
        else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    )

    return {
        "count": n,
        "mean": mean,
        "std": std_dev,
        "median": median,
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
    }


def to_snake_case(text):
    import re

    text = re.sub(
        r"([A-Z]+)([A-Z][a-z])",
        r"\1_\2",
        text,
    )

    text = re.sub(
        r"([a-z\d])([A-Z])",
        r"\1_\2",
        text,
    )

    return text.lower()


def to_camel_case(text):
    parts = text.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def truncate(
    text,
    max_len,
    ellipsis,
    ):
    if len(text) <= max_len:
        return text
    return text[: max_len - len(ellipsis)] + ellipsis


def pad_string(
    text,
    width,
    char,
    align,
    ):
    if align == "left":
        return text.ljust(width, char)
    elif align == "right":
        return text.rjust(width, char)
    return text.center(width, char)
