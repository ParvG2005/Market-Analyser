import { EmptyState } from "../components/common/EmptyState";

export function Scanner() {
  return (
    <>
      <h1 className="page-title">Scanner</h1>
      <p className="page-sub">Build indicator rules · watch live hits across your universe</p>
      <EmptyState
        glyph="⊞"
        title="No rules yet"
        message="Create your first scan rule — pick an indicator, timeframe, operator, and value, then combine rows with AND/OR. Matching symbols stream into the hits feed. The rule builder lands in Phase 4."
        action="Create a rule"
      />
    </>
  );
}
