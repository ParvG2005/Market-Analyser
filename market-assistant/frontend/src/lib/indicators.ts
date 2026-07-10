import type { Candle } from "../hooks/useCandles";

/** Exponential moving average of closes. Seeded with the first close. */
export function ema(candles: Candle[], period: number): number[] {
  const k = 2 / (period + 1);
  const out: number[] = [];
  let prev = 0;
  candles.forEach((c, i) => {
    prev = i === 0 ? c.c : c.c * k + prev * (1 - k);
    out.push(prev);
  });
  return out;
}

/** Cumulative volume-weighted average price over typical price (h+l+c)/3. */
export function vwap(candles: Candle[]): number[] {
  let cumPV = 0;
  let cumV = 0;
  return candles.map((c) => {
    const typical = (c.h + c.l + c.c) / 3;
    cumPV += typical * c.v;
    cumV += c.v;
    return cumV === 0 ? typical : cumPV / cumV;
  });
}

export interface BollingerBand {
  upper: number;
  mid: number;
  lower: number;
}

/** Bollinger bands over closes; null until `period` bars are available. */
export function bollinger(
  candles: Candle[],
  period = 20,
  stdDevMultiplier = 2,
): (BollingerBand | null)[] {
  return candles.map((_, i) => {
    if (i < period - 1) return null;
    const window = candles.slice(i - period + 1, i + 1);
    const mean = window.reduce((sum, c) => sum + c.c, 0) / period;
    const variance = window.reduce((sum, c) => sum + (c.c - mean) ** 2, 0) / period;
    const stdDev = Math.sqrt(variance);
    return {
      upper: mean + stdDevMultiplier * stdDev,
      mid: mean,
      lower: mean - stdDevMultiplier * stdDev,
    };
  });
}
