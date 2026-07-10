"""Rule DSL parser and validation for the scanner rule engine.

Parses a raw (JSON-decoded) rule definition into a typed `RuleNode` tree,
raising `RuleDSLError` with a JSONPath-like `path` pointing at the offending
field on any validation failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALID_INDICATORS = {"rsi", "ema", "sma", "vwap", "atr", "adx", "rel_volume", "gap_pct", "bollinger"}
VALID_TFS = {"1m", "5m", "15m", "1h", "1d"}
VALID_OPS = {"<", "<=", ">", ">=", "==", "!="}


class RuleDSLError(ValueError):
    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


@dataclass(frozen=True)
class Condition:
    ind: str
    tf: str
    op: str
    value: float
    params: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class AllNode:
    all: list[RuleNode]


@dataclass(frozen=True)
class AnyNode:
    any: list[RuleNode]


RuleNode = Condition | AllNode | AnyNode


def _parse_condition(raw: dict[str, Any], path: str) -> Condition:
    ind = raw.get("ind")
    if ind not in VALID_INDICATORS:
        raise RuleDSLError(f"{path}.ind", f"unknown indicator {ind!r}")
    tf = raw.get("tf")
    if tf not in VALID_TFS:
        raise RuleDSLError(f"{path}.tf", f"unknown timeframe {tf!r}")
    op = raw.get("op")
    if op not in VALID_OPS:
        raise RuleDSLError(f"{path}.op", f"unknown operator {op!r}")
    if "value" not in raw:
        raise RuleDSLError(f"{path}.value", "missing required field 'value'")
    value = raw["value"]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise RuleDSLError(f"{path}.value", f"value must be numeric, got {value!r}")
    params = raw.get("params", {})
    if not isinstance(params, dict):
        raise RuleDSLError(f"{path}.params", "params must be an object")
    return Condition(ind=ind, tf=tf, op=op, value=float(value), params=params)


def _parse_node(raw: Any, path: str) -> RuleNode:
    if not isinstance(raw, dict):
        raise RuleDSLError(path, "node must be an object")
    if "all" in raw:
        children = raw["all"]
        if not isinstance(children, list) or len(children) == 0:
            raise RuleDSLError(f"{path}.all", "'all' must be a non-empty list")
        return AllNode(all=[_parse_node(c, f"{path}.all[{i}]") for i, c in enumerate(children)])
    if "any" in raw:
        children = raw["any"]
        if not isinstance(children, list) or len(children) == 0:
            raise RuleDSLError(f"{path}.any", "'any' must be a non-empty list")
        return AnyNode(any=[_parse_node(c, f"{path}.any[{i}]") for i, c in enumerate(children)])
    if "ind" in raw:
        return _parse_condition(raw, path)
    raise RuleDSLError(path, "node must contain 'all', 'any', or 'ind'")


def parse_rule_definition(raw: dict[str, Any]) -> RuleNode:
    return _parse_node(raw, "$")
