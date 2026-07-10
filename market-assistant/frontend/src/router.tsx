import { createBrowserRouter, createMemoryRouter } from "react-router-dom";

import { Charts } from "./pages/Charts";
import { Chat } from "./pages/Chat";
import { Home } from "./pages/Home";
import { Scanner } from "./pages/Scanner";
import { Settings } from "./pages/Settings";
import { Strategies } from "./pages/Strategies";
import { Trends } from "./pages/Trends";

const routes = [
  { path: "/", element: <Home /> },
  { path: "/charts", element: <Charts /> },
  { path: "/scanner", element: <Scanner /> },
  { path: "/strategies", element: <Strategies /> },
  { path: "/trends", element: <Trends /> },
  { path: "/chat", element: <Chat /> },
  { path: "/settings", element: <Settings /> },
];

export const router = createBrowserRouter(routes);

export function createTestRouter(initialPath: string) {
  return createMemoryRouter(routes, { initialEntries: [initialPath] });
}
