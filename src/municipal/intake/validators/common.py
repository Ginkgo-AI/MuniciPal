"""Built-in validators for common field types."""

from __future__ import annotations

import re
from typing import Any

# Registry of validator functions: name -> callable(value, **params) -> str | None
# Returns an error message string on failure, None on success.
VALIDATORS: dict[str, Any] = {}


def register(name: str):
    """Decorator to register a validator function."""
    def decorator(fn):
        VALIDATORS[name] = fn
        return fn
    return decorator


@register("required")
def validate_required(value: Any, **_kwargs: Any) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return "This field is required."
    return None


@register("regex")
def validate_regex(value: Any, pattern: str = "", **_kwargs: Any) -> str | None:
    if value is None or not isinstance(value, str):
        return None
    if not re.fullmatch(pattern, value):
        return f"Value does not match required pattern: {pattern}"
    return None


@register("email")
def validate_email(value: Any, **_kwargs: Any) -> str | None:
    if value is None or not isinstance(value, str) or not value.strip():
        return None
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    if not re.fullmatch(pattern, value):
        return "Please enter a valid email address."
    return None


@register("phone")
def validate_phone(value: Any, **_kwargs: Any) -> str | None:
    if value is None or not isinstance(value, str) or not value.strip():
        return None
    digits = re.sub(r"[\s\-\(\)\+]", "", value)
    if not digits.isdigit() or len(digits) < 10:
        return "Please enter a valid phone number (at least 10 digits)."
    return None


@register("date")
def validate_date(value: Any, **_kwargs: Any) -> str | None:
    if value is None or not isinstance(value, str) or not value.strip():
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return "Please enter a valid date in YYYY-MM-DD format."
    return None


@register("numeric")
def validate_numeric(
    value: Any, min_val: float | None = None, max_val: float | None = None, **_kwargs: Any
) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "Please enter a valid number."
    if min_val is not None and num < float(min_val):
        return f"Value must be at least {min_val}."
    if max_val is not None and num > float(max_val):
        return f"Value must be at most {max_val}."
    return None
