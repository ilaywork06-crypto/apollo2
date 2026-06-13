"""Generates anonymous animal-themed display names for community profiles."""

import random

ANIMALS = [
    "נשר", "דולפין", "אריה", "פנתר", "זאב", "נמר", "עיט", "ינשוף",
    "שועל", "דרקון", "נץ", "פלמינגו", "דוב", "טיגריס", "חתול",
]


def generate_fake_name(existing_names: set[str]) -> str:
    """Generate an animal name + number combination not already in use.

    Args:
        existing_names: The set of fake names already assigned to other
            profiles.

    Returns:
        A new ``"<animal> <10-99>"`` name. Retries up to 200 times to avoid
        a collision with *existing_names*; if every retry collides, returns
        the final candidate anyway.
    """
    for _ in range(200):
        name = f"{random.choice(ANIMALS)} {random.randint(10, 99)}"
        if name not in existing_names:
            return name
    return f"{random.choice(ANIMALS)} {random.randint(10, 99)}"
