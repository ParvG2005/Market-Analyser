import { EmptyState } from "../components/common/EmptyState";

export function Charts() {
  return (
    <>
      <h1 className="page-title">Charts</h1>
      <p className="page-sub">Full-height price canvas · crypto + equities · 15-min delayed for stocks</p>
      <EmptyState
        glyph="◵"
        title="Pick a symbol to chart"
        message="Search a symbol to load its candles, volume, and indicator overlays (EMA, VWAP, Bollinger) with a regime timeline. Live charts arrive in Phase 3."
        action="Search symbol"
      />
    </>
  );
}
