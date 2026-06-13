"""Client-identifier hashing for anonymous community profiles."""

import hashlib


def hash_client_id(client_id: str) -> str:
    """Return a stable, irreversible hash for a raw client identifier.

    Args:
        client_id: The raw client identifier to anonymize.

    Returns:
        A 64-character hex SHA-256 digest of the client identifier.
    """
    return hashlib.sha256(client_id.encode()).hexdigest()
