import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../contexts/AuthContext";
import { ThemeProvider } from "../contexts/ThemeContext";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ProtectedRoute } from "../components/routing/ProtectedRoute";
import { LoginPage } from "../pages/LoginPage";
import { DashboardPage } from "../pages/DashboardPage";
import { AnalyticsPage } from "../pages/AnalyticsPage";
import { UserManagementPage } from "../pages/UserManagementPage";
import { TargetsPage } from "../pages/TargetsPage";
import { AuditLogPage } from "../pages/AuditLogPage";
import { AssistantPage } from "../pages/AssistantPage";
import { OfficerAppPage } from "../pages/OfficerAppPage";

export function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
      <AuthProvider>
        <ErrorBoundary>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/officer" element={<OfficerAppPage />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/users" element={<UserManagementPage />} />
            <Route path="/targets" element={<TargetsPage />} />
            <Route path="/audit" element={<AuditLogPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        </ErrorBoundary>
      </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
