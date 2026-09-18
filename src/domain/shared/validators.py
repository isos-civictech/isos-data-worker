"""
Reusable Pydantic validators shared across all domain entities.
"""
from typing import Annotated

from pydantic import BeforeValidator, Field


def _not_blank(value: str) -> str:
    """
    Strip whitespace and raise if the result is empty.
    Applied BEFORE Pydantic's own type validation (BeforeValidator).
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError("Value cannot be empty or blank")
    return stripped

NotBlankStr = Annotated[str, BeforeValidator(_not_blank)]

Legislature = Annotated[int, Field(ge=1)]