import { CandleChart } from "../chart/CandleChart";
import { useCandles } from "../../hooks/useCandles";

const NO_OVERLAYS = { ema: false, vwap: false, bollinger: false };

/** Compact price snapshot for a symbol referenced in a chat answer. Reuses the
 * Phase-3 lightweight-charts wrapper; overlays off to keep it glanceable. */
export function MiniChart({ symbol, tf = "1h" }: { symbol: string; tf?: string }) {
  const to = new Date();
  const from = new Date(to.getTime() - 1000 * 60 * 60 * 24 * 5);
  const { candles, delayed, delayMinutes } = useCandles(
    symbol,
    tf,
    from.toISOString(),
    to.toISOString(),
  );

  return (
    <figure className="mini-chart">
      <figcaption className="mini-chart-cap">
        {symbol} · {tf}
      </figcaption>
      <div className="mini-chart-canvas">
        <CandleChart
          candles={candles}
          overlays={NO_OVERLAYS}
          delayed={delayed}
          delayMinutes={delayMinutes}
        />
      </div>
    </figure>
  );
}
