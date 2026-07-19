import type { Candle } from "../hooks/useCandles";
import type { SignalOut } from "../hooks/useSignals";

/**
 * Shared guards for live WebSocket frames. A socket can carry a malformed or
 * off-schema frame (a non-candle payload on the candle channel, a truncated
 * JSON chunk, a stray control message). Parsing such a frame straight into
 * state sets fields to `undefined` and crashes consumers doing `last.toFixed()`
 * or `candle.c`. These validators parse-and-shape-check, returning `null` for
 * anything that doesn't match so callers can drop it silently.
 */

const OHLCV = ["o", "h", "l", "c", "v"] as const;

/** Parse a `/ws/candles` frame; `null` unless it has ts + finite o/h/l/c/v. */
export function parseCandleFrame(data: string): Candle | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(data);
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null) return null;
  const rec = parsed as Record<string, unknown>;
  if (typeof rec.ts !== "string" || !rec.ts) return null;
  for (const key of OHLCV) {
    const value = rec[key];
    if (typeof value !== "number" || !Number.isFinite(value)) return null;
  }
  return parsed as Candle;
}

/** Parse a `/ws/signals` frame; `null` unless it carries a numeric `id`. */
export function parseSignalFrame(data: string): SignalOut | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(data);
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null) return null;
  const rec = parsed as Record<string, unknown>;
  if (typeof rec.id !== "number") return null;
  return parsed as SignalOut;
}
