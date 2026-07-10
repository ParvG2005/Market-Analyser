import { describe, expect, it } from "vitest";

import type { Candle } from "../../src/hooks/useCandles";
import { bollinger, ema, vwap } from "../../src/lib/indicators";

function candle(ts: string, o: number, h: number, l: number, c: number, v: number): Candle {
  return { ts, o, h, l, c, v };
}

describe("ema", () => {
  it("matches hand-computed EMA(3) on a 5-point series", () => {
    const candles = [10, 11, 12, 13, 14].map((c, i) => candle(`t${i}`, c, c, c, c, 1));
    const result = ema(candles, 3);
    // k = 2/(3+1) = 0.5; seed = 10; 10.5; 11.25; 12.125; 13.0625
    expect(result[0]).toBeCloseTo(10);
    expect(result[1]).toBeCloseTo(10.5);
    expect(result[2]).toBeCloseTo(11.25);
    expect(result[3]).toBeCloseTo(12.125);
    expect(result[4]).toBeCloseTo(13.0625);
  });
});

describe("vwap", () => {
  it("computes cumulative volume-weighted typical price", () => {
    const candles = [candle("t0", 10, 12, 8, 10, 100), candle("t1", 10, 14, 9, 12, 200)];
    const result = vwap(candles);
    const typical0 = (12 + 8 + 10) / 3;
    const typical1 = (14 + 9 + 12) / 3;
    const expected1 = (typical0 * 100 + typical1 * 200) / 300;
    expect(result[0]).toBeCloseTo(typical0);
    expect(result[1]).toBeCloseTo(expected1);
  });
});

describe("bollinger", () => {
  it("returns null before the period fills, then mean +/- 2 stddev", () => {
    const closes = [10, 10, 10, 10, 20];
    const candles = closes.map((c, i) => candle(`t${i}`, c, c, c, c, 1));
    const result = bollinger(candles, 5, 2);
    expect(result[3]).toBeNull();
    expect(result[4]).not.toBeNull();
    expect(result[4]!.mid).toBeCloseTo(12);
    const variance = ((10 - 12) ** 2 * 4 + (20 - 12) ** 2) / 5;
    const stdDev = Math.sqrt(variance);
    expect(result[4]!.upper).toBeCloseTo(12 + 2 * stdDev);
    expect(result[4]!.lower).toBeCloseTo(12 - 2 * stdDev);
  });
});
