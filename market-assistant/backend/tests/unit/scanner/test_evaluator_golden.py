import numpy as np

from app.scanner.dsl import parse_rule_definition
from app.scanner.evaluator import compile_rule
from app.scanner.indicators import rel_volume, rsi


def _make_dip_series():
    """40 flat bars, then a sharp 15-bar drop (RSI dives <30) with one volume spike bar."""
    closes = [100.0] * 40 + list(np.linspace(100, 70, 15))
    volumes = [20.0] * 55
    volumes[50] = 200.0  # single rel-volume spike, expected trigger bar
    return closes, volumes


def test_fires_exactly_at_expected_bar_never_adjacent():
    closes, volumes = _make_dip_series()
    rsi_series = rsi(closes, period=14)
    relvol_series = rel_volume(volumes, period=20)

    definition = {
        "all": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
            {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
        ]
    }
    compiled = compile_rule(parse_rule_definition(definition))

    fired_bars = []
    for i in range(len(closes)):
        snapshot = {"5m": {"rsi": rsi_series[i], "rel_volume": relvol_series[i]}}
        if compiled.evaluate(snapshot):
            fired_bars.append(i)

    assert fired_bars == [50]
    assert 49 not in fired_bars
    assert 51 not in fired_bars


def test_any_combinator_fires_when_one_branch_true():
    definition = {
        "any": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 10},   # never true
            {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
        ]
    }
    compiled = compile_rule(parse_rule_definition(definition))
    assert compiled.evaluate({"5m": {"rsi": 50, "rel_volume": 5}}) is True
    assert compiled.evaluate({"5m": {"rsi": 50, "rel_volume": 1}}) is False


def test_required_indicators_lists_each_ind_tf_pair_once():
    definition = {
        "all": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
            {"ind": "rsi", "tf": "5m", "op": ">", "value": 5},
            {"ind": "rel_volume", "tf": "15m", "op": ">", "value": 2},
        ]
    }
    compiled = compile_rule(parse_rule_definition(definition))
    assert sorted(compiled.required_indicators()) == sorted([("rsi", "5m"), ("rel_volume", "15m")])


def test_missing_indicator_in_snapshot_evaluates_false_not_exception():
    definition = {"ind": "rsi", "tf": "5m", "op": "<", "value": 30}
    compiled = compile_rule(parse_rule_definition(definition))
    assert compiled.evaluate({"5m": {}}) is False
    assert compiled.evaluate({}) is False
