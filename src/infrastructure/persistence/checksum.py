"""
sha256_text: normalised text, drives article versioning.
sha256_bytes: raw file, drives the ingestion log.
"""
import hashlib


def sha256_text(text: str) -> str:
    """Whitespace is collapsed first, so a reflow does not create a new version."""
    normalised = " ".join(text.split())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
