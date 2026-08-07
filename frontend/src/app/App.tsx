import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../contexts/AuthContext";
import { ThemeProvider } from "../contexts/ThemeContext";
import { LanguageProvider } from "../contexts/LanguageContext";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ProtectedRoute } from "../components/routing/ProtectedRoute";
import { useAuth } from "../hooks/useAuth";
import { HOME_PATH } from "../types/user";
import { LoginPage } from "../pages/LoginPage";
import { DashboardPage } from "../pages/DashboardPage";
import { AnalyticsPage } from "../pages/AnalyticsPage";
import { UserManagementPage } from "../pages/UserManagementPage";
import { TargetsPage } from "../pages/TargetsPage";
import { AuditLogPage } from "../pages/AuditLogPage";
import { AssistantPage } from "../pages/AssistantPage";

/** Beranda berbeda per peran: admin membuka Manajemen Pengguna, manajer membuka
 *  Dashboard. Dipakai untuk "/" maupun rute yang tidak dikenal. */
function RoleHome() {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Navigate to={HOME_PATH[user?.role ?? "manager"]} replace />;
}

export function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
      <LanguageProvider>
      <AuthProvider>
        <ErrorBoundary>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          {/* Halaman operasional — manajer. */}
          <Route element={<ProtectedRoute allow={["manager"]} />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/targets" element={<TargetsPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
          </Route>

          {/* Halaman administrasi — admin. */}
          <Route element={<ProtectedRoute allow={["admin"]} />}>
            <Route path="/users" element={<UserManagementPage />} />
            <Route path="/audit" element={<AuditLogPage />} />
          </Route>

          <Route path="/" element={<RoleHome />} />
          <Route path="*" element={<RoleHome />} />
        </Routes>
        </ErrorBoundary>
      </AuthProvider>
      </LanguageProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
