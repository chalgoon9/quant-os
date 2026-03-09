from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import NewType


Symbol = NewType("Symbol", str)
Currency = NewType("Currency", str)

ZERO = Decimal("0")
ONE = Decimal("1")


def to_decimal(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize(value: Decimal | int | float | str, digits: str = "0.0001") -> Decimal:
    return to_decimal(value).quantize(Decimal(digits), rounding=ROUND_HALF_UP)
