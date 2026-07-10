import { EmptyState } from "../components/common/EmptyState";

export function Chat() {
  return (
    <>
      <h1 className="page-title">Chat</h1>
      <p className="page-sub">Ask about the market · grounded in your live indicators</p>
      <EmptyState
        glyph="✦"
        title="Start a conversation"
        message="Ask about a symbol, a setup, or the current regime. Answers stream with the tools they checked and link mini-charts. Recommendation answers carry the standard disclaimer. The assistant arrives in Phase 10."
        action="Ask a question"
      />
    </>
  );
}
