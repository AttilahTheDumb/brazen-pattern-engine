"""Canonical, deterministic JSON and numeric serialisation."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from .errors import ValidationError

GEOMETRIC_QUANTUM = Decimal("0.1")


def decimal_mm(value: int | float | str | Decimal, *, quantum: Decimal = GEOMETRIC_QUANTUM) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"not a finite number: {value!r}") from exc
    if not number.is_finite():
        raise ValidationError(f"number must be finite: {value!r}")
    return number.quantize(quantum, rounding=ROUND_HALF_UP)


def canonical_number(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, float):
        return format(decimal_mm(value), "f")
    if isinstance(value, int):
        return str(value)
    return value


def canonicalise(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): canonicalise(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [canonicalise(item) for item in value]
    if isinstance(value, (Decimal, float, int)):
        return canonical_number(value)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(canonicalise(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
