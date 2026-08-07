import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { HOME_PATH } from "../../types/user";
import type { PortalRole } from "../../types/user";

export function ProtectedRoute({ allow }: { allow?: PortalRole[] } = {}) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Sesi lama di localStorage terbit sebelum peran admin ada dan tidak punya
  // field role; anggap manajer supaya pengguna yang sudah login tidak terlempar
  // ke halaman kosong hanya karena aplikasinya diperbarui di bawah kakinya.
  const role: PortalRole = user?.role ?? "manager";

  // Tanpa penjaga ini manajer yang membuka /users mendapat halaman yang tampil
  // utuh tapi 403 di setiap panggilan — terbaca sebagai aplikasi rusak, bukan
  // sebagai halaman yang memang bukan haknya.
  if (allow && !allow.includes(role)) {
    return <Navigate to={HOME_PATH[role]} replace />;
  }

  return <Outlet />;
}
