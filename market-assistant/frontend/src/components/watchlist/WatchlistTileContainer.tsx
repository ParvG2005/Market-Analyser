import { useEffect, useRef, useState } from "react";

import { authedFetch, buildWsUrl } from "../../lib/api";
import type { Candle } from "../../hooks/useCandles";
import { useAccessToken } from "../../hooks/useAccessToken";
import { useWebSocket } from "../../hooks/useWebSocket";
import { WatchlistTile } from "./WatchlistTile";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Owns a dedicated WS subscription for one symbol and derives daily % change. */
export function WatchlistTileContainer({ symbol }: { symbol: string }) {
  const [last, setLast] = useState<number | null>(null);
  const [dayOpen, setDayOpen] = useState<number | null>(null);
  const lastDayRef = useRef<string | null>(null);

  // Seed the TRUE day open from REST (the 1d candle's open). The live stream
  // only starts at subscription time, so a mid-day subscription would otherwise
  // measure day% from an arbitrary intraday open. REST is authoritative for the
  // current UTC day; the WS path below is a fallback (and handles rollover).
  useEffect(() => {
    setLast(null);
    setDayOpen(null);
    lastDayRef.current = null;
    let cancelled = false;
    const now = new Date();
    const dayStart = new Date(
      Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
    );
    const params = new URLSearchParams({
      symbol,
      tf: "1d",
      from: dayStart.toISOString(),
      to: now.toISOString(),
    });
    authedFetch(`${API_BASE}/candles?${params.toString()}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((body: { candles?: Candle[] } | null) => {
        if (cancelled || !body?.candles?.length) return;
        const dayCandle = body.candles[0];
        setDayOpen(dayCandle.o);
        lastDayRef.current = dayCandle.ts.slice(0, 10);
      })
      .catch(() => {
        /* offline — fall back to the first live candle's open below */
      });
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  const onMessage = (data: string) => {
    const candle: Candle = JSON.parse(data);
    const day = candle.ts.slice(0, 10);
    // Only (re)baseline on a real day change or before REST/first-candle has
    // set one — never clobber the authoritative same-day open.
    if (lastDayRef.current !== day) {
      lastDayRef.current = day;
      setDayOpen(candle.o);
    }
    setLast(candle.c);
  };

  const token = useAccessToken();
  const wsUrl = token ? buildWsUrl(`${WS_BASE}/ws/candles`, token) : "";
  const { status, send } = useWebSocket(wsUrl, { onMessage });

  useEffect(() => {
    if (status === "open") send({ subscribe: `candles:${symbol}:1m` });
  }, [status, symbol, send]);

  if (last === null || dayOpen === null) {
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

  const changePct = (last - dayOpen) / dayOpen;
  return <WatchlistTile symbol={symbol} last={last} changePct={changePct} />;
}
