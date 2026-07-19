import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuthStore } from "../../stores/authStore";
import { useThemeStore } from "../../stores/themeStore";
import { Badge } from "../common/Badge";
import { Disclaimer } from "../Disclaimer";
import { PriceTape } from "./PriceTape";

interface NavEntry {
  to: string;
  label: string;
  icon: string;
}

// Order mirrors the Phase 2.5 functional inventory (9 tabs).
const NAV: NavEntry[] = [
  { to: "/", label: "Home", icon: "◧" },
  { to: "/charts", label: "Charts", icon: "◵" },
  { to: "/watchlist", label: "Watchlist", icon: "★" },
  { to: "/universe", label: "Universe", icon: "◎" },
  { to: "/scanner", label: "Scanner", icon: "⊞" },
  { to: "/strategies", label: "Strategies", icon: "❏" },
  { to: "/trends", label: "Trends", icon: "↗" },
  { to: "/analytics", label: "Analytics", icon: "▤" },
  { to: "/ml", label: "ML", icon: "◈" },
  { to: "/chat", label: "Chat", icon: "✦" },
];

export function AppShell() {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const user = useAuthStore((s) => s.user);
  const signOut = useAuthStore((s) => s.signOut);
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const closeDrawer = () => setDrawerOpen(false);

  const handleLogout = async () => {
    await signOut();
    navigate("/login");
  };

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
            {(user?.email ?? "?").charAt(0).toUpperCase()}
          </div>
          <div style={{ fontSize: "12px", overflow: "hidden" }}>
            <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis" }}>
              {user?.email ?? "Signed out"}
            </div>
            <button
              type="button"
              onClick={handleLogout}
              style={{
                color: "var(--ink-faint)",
                fontSize: "10.5px",
                background: "none",
                border: "none",
                padding: 0,
                cursor: "pointer",
              }}
            >
              Log out
            </button>
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
        <PriceTape />

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
            data-testid="theme-toggle"
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
