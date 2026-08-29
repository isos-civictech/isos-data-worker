"""
Fingerprints — two of them, for two different questions.

  sha256_text   drives article versioning: "is this text actually different?"
  sha256_bytes  drives the ingestion log:  "did the AN republish the same file?"
"""
import hashlib


def sha256_text(text: str) -> str:
    """
    Fingerprint of a NORMALISED text.

    Whitespace is collapsed before hashing. Without this, a reformatted line
    break in the source creates a brand new article version that says exactly
    the same thing — and the RAG would re-embed for nothing.
    """
    normalised = " ".join(text.split())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    """Fingerprint of a raw file, byte for byte."""
    return hashlib.sha256(payload).hexdigest()
