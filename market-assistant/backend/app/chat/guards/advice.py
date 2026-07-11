"""Advice guard: enforce educational framing — no imperative buy/sell or
guarantee language, and (optionally) require the disclaimer on recommendation
answers.
"""

from __future__ import annotations

from dataclasses import dataclass

DISCLAIMER_TEXT = "Educational analysis. Not investment advice. Past performance ≠ future results."

_FORBIDDEN_PHRASES = [
    "you should buy",
    "you should sell",
    "guaranteed",
    "buy now",
    "sell now",
    "guaranteed to go up",
    "guaranteed to go down",
]


@dataclass
class AdviceResult:
    ok: bool
    violations: list[str]


def check_advice_language(answer: str, requires_disclaimer: bool = False) -> AdviceResult:
    lowered = answer.lower()
    violations = [phrase for phrase in _FORBIDDEN_PHRASES if phrase in lowered]
    if requires_disclaimer and DISCLAIMER_TEXT.lower() not in lowered:
        violations.append("missing disclaimer")
    return AdviceResult(ok=len(violations) == 0, violations=violations)
