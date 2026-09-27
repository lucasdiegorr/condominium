import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { RequireIdentity, RequireScope } from "./auth/ProtectedRoute";
import CondominiumSelectPage from "./pages/CondominiumSelectPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public route — the only one reachable without authentication. */}
          <Route path="/login" element={<LoginPage />} />

          {/* Identity-authenticated flows. */}
          <Route element={<RequireIdentity />}>
            <Route path="/select" element={<CondominiumSelectPage />} />
          </Route>

          {/* Scoped (condominium) application. */}
          <Route element={<RequireIdentity />}>
            <Route element={<RequireScope />}>
              <Route path="/app" element={<HomePage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
