import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useThemeStore } from "../../stores/themeStore";
import { Badge } from "../common/Badge";
import { Disclaimer } from "../Disclaimer";

interface NavEntry {
  to: string;
  label: string;
  icon: string;
}

// Order mirrors the Phase 2.5 functional inventory (9 tabs).
const NAV: NavEntry[] = [
  { to: "/", label: "Home", icon: "◧" },
  { to: "/charts", label: "Charts", icon: "◵" },
  { to: "/scanner", label: "Scanner", icon: "⊞" },
  { to: "/strategies", label: "Strategies", icon: "❏" },
  { to: "/trends", label: "Trends", icon: "↗" },
  { to: "/analytics", label: "Analytics", icon: "▤" },
  { to: "/ml", label: "ML", icon: "◈" },
  { to: "/chat", label: "Chat", icon: "✦" },
];

const TAPE = [
  { sym: "BTC", px: "67,412", chg: "+2.14%", dir: "up" },
  { sym: "ETH", px: "3,284", chg: "+1.02%", dir: "up" },
  { sym: "SOL", px: "184.6", chg: "−0.73%", dir: "down" },
  { sym: "SPY", px: "548.9", chg: "+0.31%", dir: "up" },
  { sym: "NVDA", px: "126.4", chg: "−1.18%", dir: "down" },
] as const;

export function AppShell() {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const closeDrawer = () => setDrawerOpen(false);

  return (
    <div className="app" data-drawer={drawerOpen ? "open" : "closed"}>
      <aside className="rail">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            M
          </div>
          <div className="brand-name">
            Market Assistant
            <small>Analysis desk</small>
          </div>
        </div>

        <nav className="nav" aria-label="Primary">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={closeDrawer}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
            >
              <span className="ic" aria-hidden="true">
                {item.icon}
              </span>
              {item.label}
            </NavLink>
          ))}
          <div className="nav-sep">System</div>
          <NavLink
            to="/settings"
            onClick={closeDrawer}
            className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
          >
            <span className="ic" aria-hidden="true">
              ⚙
            </span>
            Settings
          </NavLink>
        </nav>

        <div className="rail-foot">
          <div className="avatar" aria-hidden="true">
            P
          </div>
          <div style={{ fontSize: "12px" }}>
            <div style={{ fontWeight: 600 }}>Parv G</div>
            <div style={{ color: "var(--ink-faint)", fontSize: "10.5px" }}>Free plan</div>
          </div>
        </div>
      </aside>

      <button
        type="button"
        className="scrim"
        aria-label="Close navigation"
        onClick={closeDrawer}
      />

      <div className="main">
        <div className="tape">
          {TAPE.map((t) => (
            <div className="tape-item" key={t.sym}>
              <span className="sym">{t.sym}</span>
              <span className="px num">{t.px}</span>
              <span className={`chg num ${t.dir}`}>{t.chg}</span>
            </div>
          ))}
        </div>

        <div className="topbar">
          <button
            type="button"
            className="icon-btn menu-btn"
            aria-label="Open navigation"
            onClick={() => setDrawerOpen(true)}
          >
            ☰
          </button>
          <input className="search" placeholder="Search symbol — BTC-USD, AAPL…" aria-label="Search symbol" />
          <Badge>◷ Equities 15-min delayed</Badge>
          <button
            type="button"
            className="icon-btn"
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
            aria-pressed={theme === "dark"}
            onClick={toggleTheme}
          >
            {theme === "dark" ? "☾" : "☀"}
          </button>
        </div>

        <main className="content">
          <Outlet />
        </main>

        <Disclaimer />
      </div>
    </div>
  );
}
