"""API key generation and verification helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_api_key(*, prefix: str = "ak") -> str:
    """Generate a high-entropy plaintext API key."""

    return f"{prefix}_{secrets.token_urlsafe(32)}"


def api_key_prefix(plaintext_key: str, *, length: int = 12) -> str:
    """Return a non-secret prefix suitable for lookup hints and UI display."""

    return plaintext_key[:length]


def hash_api_key(plaintext_key: str) -> str:
    """Hash a high-entropy API key for storage."""

    return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()


def verify_api_key(plaintext_key: str, expected_hash: str) -> bool:
    """Verify a plaintext API key against a stored hash."""

    return hmac.compare_digest(hash_api_key(plaintext_key), expected_hash)
