import { useEffect, useRef, useState } from "react";

import type { Candle } from "../../hooks/useCandles";
import { useWebSocket } from "../../hooks/useWebSocket";
import { WatchlistTile } from "./WatchlistTile";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

/** Owns a dedicated WS subscription for one symbol and derives daily % change. */
export function WatchlistTileContainer({ symbol }: { symbol: string }) {
  const [last, setLast] = useState<number | null>(null);
  const dayOpenRef = useRef<number | null>(null);
  const lastDayRef = useRef<string | null>(null);

  const onMessage = (data: string) => {
    const candle: Candle = JSON.parse(data);
    const day = candle.ts.slice(0, 10);
    if (dayOpenRef.current === null || lastDayRef.current !== day) {
      dayOpenRef.current = candle.o;
      lastDayRef.current = day;
    }
    setLast(candle.c);
  };

  const { status, send } = useWebSocket(`${WS_BASE}/ws/candles`, { onMessage });

  useEffect(() => {
    if (status === "open") send({ subscribe: `candles:${symbol}:1m` });
  }, [status, symbol, send]);

  if (last === null || dayOpenRef.current === null) {
    return (
      <div className="wl-tile wl-tile-loading skel" data-testid={`tile-${symbol}-loading`}>
        <div className="wl-tile-top">
          <span className="wl-sym">{symbol}</span>
        </div>
        <div className="bar w60" />
        <div className="bar w40" />
      </div>
    );
  }

  const changePct = (last - dayOpenRef.current) / dayOpenRef.current;
  return <WatchlistTile symbol={symbol} last={last} changePct={changePct} />;
}
