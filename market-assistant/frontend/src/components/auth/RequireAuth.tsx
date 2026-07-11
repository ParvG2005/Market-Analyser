import { Navigate, Outlet } from "react-router-dom";

import { useAuthStore } from "../../stores/authStore";

/** Route guard: renders its children via `<Outlet/>` when signed in, else
 * redirects to `/login`. Mounted as the parent element of every app route. */
export function RequireAuth() {
  const authed = useAuthStore((s) => s.isAuthenticated);
  return authed ? <Outlet /> : <Navigate to="/login" replace />;
}
