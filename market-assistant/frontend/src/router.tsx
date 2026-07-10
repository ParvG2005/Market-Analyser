import { createBrowserRouter, createMemoryRouter } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { Analytics } from "./pages/Analytics";
import { Charts } from "./pages/Charts";
import { Chat } from "./pages/Chat";
import { Home } from "./pages/Home";
import { ML } from "./pages/ML";
import { Scanner } from "./pages/Scanner";
import { Settings } from "./pages/Settings";
import { Strategies } from "./pages/Strategies";
import { Trends } from "./pages/Trends";

const routes = [
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/charts", element: <Charts /> },
      { path: "/scanner", element: <Scanner /> },
      { path: "/strategies", element: <Strategies /> },
      { path: "/trends", element: <Trends /> },
      { path: "/analytics", element: <Analytics /> },
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
