import { EmptyState } from "../components/common/EmptyState";

export function Strategies() {
  return (
    <>
      <h1 className="page-title">Strategies</h1>
      <p className="page-sub">Preset setups · tune params · run mini-backtests</p>
      <EmptyState
        glyph="❏"
        title="No strategies enabled"
        message="Enable a preset — ORB, VWAP revert, EMA 9/21 + VWAP, breakout-retest, and more — to tune its parameters and see detected setups with historical win-rate context. Presets arrive in Phase 6."
        action="Browse presets"
      />
    </>
  );
}
