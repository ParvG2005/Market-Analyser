import { EmptyState } from "../components/common/EmptyState";

export function Analytics() {
  return (
    <>
      <h1 className="page-title">Analytics</h1>
      <p className="page-sub">Compare strategies · correlations · seasonality · backtest results</p>
      <EmptyState
        glyph="▤"
        title="Nothing to analyze yet"
        message="Run a backtest or enable strategies to compare equity curves, correlation matrices, seasonality heatmaps, and trade tables here. Analytics ships in Phase 13."
      />
    </>
  );
}
