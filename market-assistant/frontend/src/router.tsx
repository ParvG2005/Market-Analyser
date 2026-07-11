import { createBrowserRouter, createMemoryRouter } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { Analytics } from "./pages/Analytics";
import { BacktestResults } from "./pages/BacktestResults";
import { ChartsPage } from "./pages/Charts";
import { Chat } from "./pages/Chat";
import { Home } from "./pages/Home";
import { ML } from "./pages/ML";
import { Scanner } from "./pages/Scanner";
import { Settings } from "./pages/Settings";
import { Strategies } from "./pages/Strategies";
import { Trends } from "./pages/Trends";
import Universe from "./pages/Universe";
import { WatchlistPage } from "./pages/Watchlist";

const routes = [
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/charts", element: <ChartsPage /> },
      { path: "/watchlist", element: <WatchlistPage /> },
      { path: "/universe", element: <Universe /> },
      { path: "/scanner", element: <Scanner /> },
      { path: "/strategies", element: <Strategies /> },
      { path: "/trends", element: <Trends /> },
      { path: "/analytics", element: <Analytics /> },
      { path: "/backtests/:id", element: <BacktestResults /> },
      { path: "/ml", element: <ML /> },
      { path: "/chat", element: <Chat /> },
      { path: "/settings", element: <Settings /> },
    ],
  },
];

export const router = createBrowserRouter(routes);

export function createTestRouter(initialPath: string) {
  return createMemoryRouter(routes, { initialEntries: [initialPath] });
}
