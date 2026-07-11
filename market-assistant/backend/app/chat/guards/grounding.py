"""Grounding guard: flag numeric *market-fact* claims in an answer that are not
backed by this turn's tool outputs. The orchestrator regenerates once on
failure, then substitutes ``FALLBACK_MESSAGE``.

Only price/indicator-value-shaped numbers count as claims: a decimal
(``62.4``, ``65000.0``), a 4+ digit number (a price like ``71234``), or a
``$``-prefixed number. Bare small integers (indicator periods like ``9/21/14``,
scale references like ``0-100``) are treated as prose, not verifiable facts.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from app.schemas.chat import ToolResult

FALLBACK_MESSAGE = "I don't have that data."

# A number token bounded by non-alphanumerics (so "1h"/"1m"/"BTC" are excluded),
# with optional leading $ and thousands separators and an optional decimal part.
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9.])(\$?)(\d[\d,]*(?:\.\d+)?)(?![A-Za-z0-9])")
_TOLERANCE = 0.05


@dataclass
class GroundingResult:
    grounded: bool
    unsupported_claims: list[str]


def _walk(obj: Any) -> Iterator[Any]:
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)
    else:
        yield obj


def _known_numbers(facts: list[ToolResult]) -> list[float]:
    numbers: list[float] = []
    for fact in facts:
        if not fact.ok or not fact.data:
            continue
        for value in _walk(fact.data):
            if isinstance(value, bool):
                continue
            if isinstance(value, int | float):
                numbers.append(float(value))
    return numbers


def _is_market_fact_claim(dollar: str, token: str) -> bool:
    if dollar == "$":
        return True
    if "." in token:
        return True
    return len(token.replace(",", "")) >= 4


def check_grounding(answer: str, facts: list[ToolResult]) -> GroundingResult:
    known = _known_numbers(facts)
    unsupported: list[str] = []
    for dollar, token in _NUMBER_RE.findall(answer):
        if not _is_market_fact_claim(dollar, token):
            continue
        try:
            claim = float(token.replace(",", ""))
        except ValueError:
            continue
        if not any(abs(claim - k) <= _TOLERANCE for k in known):
            unsupported.append(token)
    return GroundingResult(grounded=len(unsupported) == 0, unsupported_claims=unsupported)
