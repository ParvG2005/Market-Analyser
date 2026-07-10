from decimal import Decimal

from app.ingest.candle import Candle

_WINDOW_MINUTES = {"5m": 5, "15m": 15, "1h": 60}


def aggregate_candles(candles: list[Candle], target_tf: str) -> list[Candle]:
    """Roll up sorted, contiguous 1m candles into target_tf bars.

    Precondition: ``candles`` must be sorted ascending by ``ts`` and be a
    contiguous, gap-free run of 1m candles. Windowing is positional (each
    consecutive block of ``window_minutes`` candles becomes one bar); gaps
    are filled upstream before aggregation, so this function does not detect
    or repair them.

    Only full windows are emitted; a trailing partial window (fewer than
    window_minutes 1m bars) is dropped, since it will be completed and
    re-aggregated once more 1m data arrives.
    """
    if target_tf not in _WINDOW_MINUTES:
        raise ValueError(f"unsupported target_tf: {target_tf}")

    window = _WINDOW_MINUTES[target_tf]
    ordered = sorted(candles, key=lambda c: c.ts)

    result: list[Candle] = []
    for i in range(0, len(ordered) - window + 1, window):
        chunk = ordered[i:i + window]
        if len(chunk) < window:
            break
        result.append(
            Candle(
                symbol=chunk[0].symbol,
                tf=target_tf,
                ts=chunk[0].ts,
                o=chunk[0].o,
                h=max(c.h for c in chunk),
                l=min(c.l for c in chunk),
                c=chunk[-1].c,
                v=sum((c.v for c in chunk), Decimal("0")),
            )
        )
    return result
