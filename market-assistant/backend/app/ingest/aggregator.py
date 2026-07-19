from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.candle import Candle
from app.models.candle import CandleRow

_WINDOW_MINUTES = {"5m": 5, "15m": 15, "1h": 60, "1d": 1440}

DEFAULT_HIGHER_TFS: tuple[str, ...] = ("5m", "15m", "1h", "1d")


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


def _floor_to_window(ts: datetime, minutes: int) -> datetime:
    """Floor a UTC timestamp to the start of its ``minutes``-long window.

    Windows are anchored to the Unix epoch, so 1d (1440m) floors to UTC
    midnight and intraday steps floor to their aligned boundaries.
    """
    epoch_minutes = int(ts.timestamp()) // 60
    floored = (epoch_minutes // minutes) * minutes
    return datetime.fromtimestamp(floored * 60, tz=UTC)


@dataclass(frozen=True, slots=True)
class Emission:
    """One higher-tf candle produced from a just-closed window."""

    instrument_id: int
    symbol: str
    tf: str
    window_start: datetime
    candle: Candle


class LiveAggregator:
    """Rolls live 1m closes up into higher-tf candles.

    A higher-tf window ``[W, W+Δ)`` is only emitted once it is provably closed:
    i.e. a 1m candle has arrived in the *next* window. The window's 1m rows are
    read back from the DB (so backfilled bars are included) and rolled up with
    :func:`aggregate_candles`; a window missing any 1m bar produces nothing
    (partial windows are dropped) and is retried on a later flush.

    ``confirm`` advances the per-(instrument, tf) high-water mark only after the
    caller has durably persisted the emitted candles, so a persist failure
    re-emits the window rather than silently dropping it.
    """

    def __init__(self, target_tfs: tuple[str, ...] = DEFAULT_HIGHER_TFS) -> None:
        self._target_tfs = target_tfs
        self._last_emitted: dict[tuple[int, str], datetime] = {}

    async def produce(
        self,
        session: AsyncSession,
        symbol_to_instrument_id: dict[str, int],
        batch: dict[str, list[Candle]],
    ) -> list[Emission]:
        emissions: list[Emission] = []
        for symbol, candles in batch.items():
            instrument_id = symbol_to_instrument_id.get(symbol)
            if instrument_id is None or not candles:
                continue
            max_ts = max(c.ts for c in candles)
            for tf in self._target_tfs:
                step = _WINDOW_MINUTES[tf]
                current_window = _floor_to_window(max_ts, step)
                completed_window = current_window - timedelta(minutes=step)
                seen = self._last_emitted.get((instrument_id, tf))
                if seen is not None and completed_window <= seen:
                    continue

                rows = (
                    await session.execute(
                        select(CandleRow)
                        .where(
                            CandleRow.instrument_id == instrument_id,
                            CandleRow.tf == "1m",
                            CandleRow.ts >= completed_window,
                            CandleRow.ts < current_window,
                        )
                        .order_by(CandleRow.ts)
                    )
                ).scalars().all()

                minute_candles = [
                    Candle(
                        symbol=symbol,
                        tf="1m",
                        ts=r.ts,
                        o=r.o or Decimal("0"),
                        h=r.h or Decimal("0"),
                        l=r.l or Decimal("0"),
                        c=r.c or Decimal("0"),
                        v=r.v or Decimal("0"),
                    )
                    for r in rows
                ]
                rolled = aggregate_candles(minute_candles, tf)
                if not rolled:
                    continue
                emissions.append(
                    Emission(
                        instrument_id=instrument_id,
                        symbol=symbol,
                        tf=tf,
                        window_start=completed_window,
                        candle=rolled[0],
                    )
                )
        return emissions

    def confirm(self, emissions: list[Emission]) -> None:
        for e in emissions:
            prev = self._last_emitted.get((e.instrument_id, e.tf))
            if prev is None or e.window_start > prev:
                self._last_emitted[(e.instrument_id, e.tf)] = e.window_start
