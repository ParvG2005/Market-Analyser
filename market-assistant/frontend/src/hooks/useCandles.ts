import { useEffect, useMemo, useRef, useState } from "react";

import { authedFetch, buildWsUrl } from "../lib/api";
import { useAccessToken } from "./useAccessToken";
import { useWebSocket } from "./useWebSocket";

export interface Candle {
  ts: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/**
 * Loads REST candle history for `symbol`/`tf`, then layers the live
 * `/ws/candles` stream on top — deduping by timestamp (a forming bar replaces
 * its prior version; a new bar appends), keeping the series time-ordered.
 */
export function useCandles(symbol: string, tf: string, from: string, to: string) {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [delayed, setDelayed] = useState(false);
  const [delayMinutes, setDelayMinutes] = useState(0);
  const candlesRef = useRef<Candle[]>([]);

  useEffect(() => {
    candlesRef.current = [];
    setCandles([]);
    setDelayed(false);
    setDelayMinutes(0);
    if (typeof fetch !== "function") return;

    let cancelled = false;
    const params = new URLSearchParams({ symbol, tf, from, to });
    authedFetch(`${API_BASE}/candles?${params.toString()}`)
      .then((res) => res.json())
      .then((body: { candles: Candle[]; delayed?: boolean; delay_minutes?: number }) => {
        if (cancelled) return;
        const history = body.candles;
        candlesRef.current = history;
        setCandles(history);
        setDelayed(body.delayed ?? false);
        setDelayMinutes(body.delay_minutes ?? 0);
      })
      .catch(() => {
        /* offline / backend down — keep the empty series, WS may still fill it */
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, tf, from, to]);

  const onMessage = useMemo(
    () => (data: string) => {
      const incoming: Candle = JSON.parse(data);
      const existing = candlesRef.current;
      const idx = existing.findIndex((c) => c.ts === incoming.ts);
      const next =
        idx >= 0
          ? [...existing.slice(0, idx), incoming, ...existing.slice(idx + 1)]
          : [...existing, incoming].sort((a, b) => a.ts.localeCompare(b.ts));
      candlesRef.current = next;
      setCandles(next);
    },
    [],
  );

  const token = useAccessToken();
  const wsUrl = token ? buildWsUrl(`${WS_BASE}/ws/candles`, token) : "";
  const { send, status } = useWebSocket(wsUrl, { onMessage });

  useEffect(() => {
    if (status === "open") {
      send({ subscribe: `candles:${symbol}:${tf}` });
    }
  }, [status, symbol, tf, send]);

  return { candles, status, delayed, delayMinutes };
}
