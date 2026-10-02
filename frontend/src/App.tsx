import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import { AuthProvider } from "./auth/AuthContext";
import { RequireIdentity, RequireScope } from "./auth/ProtectedRoute";
import AssociationsPage from "./pages/AssociationsPage";
import BookingsPage from "./pages/BookingsPage";
import CommonAreasPage from "./pages/CommonAreasPage";
import CondominiumsPage from "./pages/CondominiumsPage";
import CondominiumSelectPage from "./pages/CondominiumSelectPage";
import FinancialPage from "./pages/FinancialPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import PetsPage from "./pages/PetsPage";
import ResidentsPage from "./pages/ResidentsPage";
import RolesPage from "./pages/RolesPage";
import UnitsPage from "./pages/UnitsPage";
import VehiclesPage from "./pages/VehiclesPage";

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
              <Route path="/app" element={<AppLayout />}>
                <Route index element={<HomePage />} />
                <Route path="units" element={<UnitsPage />} />
                <Route path="residents" element={<ResidentsPage />} />
                <Route path="vehicles" element={<VehiclesPage />} />
                <Route path="pets" element={<PetsPage />} />
                <Route path="common-areas" element={<CommonAreasPage />} />
                <Route path="bookings" element={<BookingsPage />} />
                <Route path="financial" element={<FinancialPage />} />
                <Route path="roles" element={<RolesPage />} />
                <Route path="associations" element={<AssociationsPage />} />
                <Route path="condominiums" element={<CondominiumsPage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
