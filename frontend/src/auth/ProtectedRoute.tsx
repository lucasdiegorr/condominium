import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

/** Requires an identity token; otherwise redirects to the public login screen. */
export function RequireIdentity() {
  const { identityToken } = useAuth();
  const location = useLocation();
  if (!identityToken) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

/** Requires a scoped (condominium) token; otherwise redirects to selection. */
export function RequireScope() {
  const { scopedToken } = useAuth();
  if (!scopedToken) {
    return <Navigate to="/select" replace />;
  }
  return <Outlet />;
}
