import { EmptyState } from "../components/common/EmptyState";

export function Settings() {
  return (
    <>
      <h1 className="page-title">Settings</h1>
      <p className="page-sub">Universe · alerts · profile · appearance</p>
      <EmptyState
        glyph="⚙"
        title="Settings are on the way"
        message="Manage your instrument universe, alert subscriptions (Telegram, per-rule toggles), profile, and theme preference here. Wired up in Phase 11; theme toggle already lives in the top bar."
      />
    </>
  );
}
