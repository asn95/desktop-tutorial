import { FormEvent, useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import indihomeLogo from "../assets/indihome-logo.png";

const FAILED_KEY = "c3mr:login-failures";
const MAX_ATTEMPTS = 5;
const LOCKOUT_MS = 60_000;

function getFailures(): { count: number; lastAt: number } {
  try {
    const raw = localStorage.getItem(FAILED_KEY);
    return raw ? JSON.parse(raw) : { count: 0, lastAt: 0 };
  } catch {
    return { count: 0, lastAt: 0 };
  }
}

function recordFailure() {
  const f = getFailures();
  localStorage.setItem(FAILED_KEY, JSON.stringify({ count: f.count + 1, lastAt: Date.now() }));
}

function clearFailures() {
  localStorage.removeItem(FAILED_KEY);
}

function isLockedOut(): { locked: boolean; remainingSec: number } {
  const f = getFailures();
  if (f.count >= MAX_ATTEMPTS) {
    const elapsed = Date.now() - f.lastAt;
    if (elapsed < LOCKOUT_MS) {
      return { locked: true, remainingSec: Math.ceil((LOCKOUT_MS - elapsed) / 1000) };
    }
    clearFailures();
  }
  return { locked: false, remainingSec: 0 };
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberDevice, setRememberDevice] = useState(
    () => localStorage.getItem("c3mr:remember-device") === "true"
  );
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRecovery, setShowRecovery] = useState(false);
  const [lockoutSec, setLockoutSec] = useState(() => isLockedOut().remainingSec);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const redirectPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    const lockCheck = isLockedOut();
    if (lockCheck.locked) {
      setLockoutSec(lockCheck.remainingSec);
      setError(`Terlalu banyak percobaan gagal. Coba lagi dalam ${lockCheck.remainingSec} detik.`);
      return;
    }

    try {
      setIsSubmitting(true);
      await login({ username, password });
      clearFailures();
      if (rememberDevice) {
        localStorage.setItem("c3mr:remember-device", "true");
      } else {
        localStorage.removeItem("c3mr:remember-device");
      }
      navigate(redirectPath, { replace: true });
    } catch (err) {
      recordFailure();
      const failures = getFailures();
      const remaining = MAX_ATTEMPTS - failures.count;
      const message = err instanceof Error ? err.message : "Tidak dapat masuk. Silakan coba lagi.";
      if (remaining > 0) {
        setError(`${message} (${remaining} percobaan tersisa)`);
      } else {
        const lockCheck = isLockedOut();
        setLockoutSec(lockCheck.remainingSec);
        setError(`Akun terkunci sementara. Coba lagi dalam ${lockCheck.remainingSec} detik.`);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const locked = lockoutSec > 0 && isLockedOut().locked;

  return (
    <div
      className="flex min-h-[100dvh] items-center justify-center bg-[#f3f4f6] px-4 py-10"
      style={{ fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif" }}
    >
      <div
        className={
          "w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-[0_12px_40px_-12px_rgba(15,23,42,0.18)] ring-1 ring-black/5 transition-all duration-500 ease-out " +
          (mounted ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0")
        }
      >
        <div className="grid lg:grid-cols-2">
          {/* ───────────── LEFT — IndiHome by Telkomsel brand panel ───────────── */}
          <div className="relative flex flex-col justify-between gap-8 overflow-hidden bg-[#EA0A2C] p-8 text-white sm:p-10 lg:p-12">
            {/* Logo lockup (logo is red, so it sits on a white card) */}
            <div className="relative">
              <span className="inline-flex items-center justify-center rounded-2xl bg-white px-5 py-3.5 shadow-[0_8px_24px_-10px_rgba(0,0,0,0.35)]">
                <img src={indihomeLogo} alt="IndiHome by Telkomsel" className="h-9 w-auto object-contain" />
              </span>
            </div>

            {/* Product */}
            <div className="relative">
              <h1 className="text-3xl font-bold tracking-tight">C3MR</h1>
              <p className="mt-1.5 text-sm font-semibold text-white/90">Sistem Manajemen Terpadu</p>
              <p className="mt-4 max-w-xs text-sm leading-relaxed text-white/75">
                Portal operasional untuk penagihan, akun pelanggan, dan pelaporan.
              </p>
            </div>

            {/* Copyright */}
            <p className="relative text-xs text-white/70">&copy; 2026 IndiHome by Telkomsel &middot; PT Telekomunikasi Selular</p>
          </div>

          {/* ───────────── RIGHT — sign-in form ───────────── */}
          <div className="bg-white p-8 sm:p-10 lg:p-12">
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-gray-900">Masuk ke akun Anda</h2>
              <p className="mt-1.5 text-sm text-gray-500">Masukkan kredensial untuk mengakses C3MR.</p>
            </div>

            <form className="space-y-5" onSubmit={onSubmit}>
              {/* Username */}
              <div>
                <label htmlFor="username" className="mb-1.5 block text-sm font-medium text-gray-700">
                  Nama Pengguna
                </label>
                <input
                  id="username"
                  type="text"
                  required
                  autoComplete="username"
                  className="w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 transition focus:border-[#EA0A2C] focus:outline-none focus:ring-2 focus:ring-[#EA0A2C]/20 disabled:bg-gray-50 disabled:text-gray-400"
                  placeholder="admin"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  disabled={locked}
                />
              </div>

              {/* Password */}
              <div>
                <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-gray-700">
                  Kata Sandi
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    required
                    autoComplete="current-password"
                    className="w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 pr-11 text-sm text-gray-900 placeholder-gray-400 transition focus:border-[#EA0A2C] focus:outline-none focus:ring-2 focus:ring-[#EA0A2C]/20 disabled:bg-gray-50 disabled:text-gray-400"
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    disabled={locked}
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 transition-colors hover:text-gray-600"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    aria-label={showPassword ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                  >
                    {showPassword ? (
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Remember + recovery */}
              <div className="flex items-center justify-between">
                <label className="flex cursor-pointer select-none items-center gap-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-gray-300 text-[#EA0A2C] accent-[#EA0A2C]"
                    checked={rememberDevice}
                    onChange={(e) => setRememberDevice(e.target.checked)}
                  />
                  Ingat perangkat ini
                </label>
                <button
                  type="button"
                  className="text-sm font-medium text-[#EA0A2C] transition-colors hover:text-[#C80825]"
                  onClick={() => setShowRecovery(true)}
                >
                  Opsi pemulihan
                </button>
              </div>

              {/* Error */}
              {error ? (
                <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 shrink-0">
                    <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{error}</span>
                </div>
              ) : null}

              {/* Submit */}
              <button
                type="submit"
                className="group flex w-full items-center justify-center gap-2 rounded-lg bg-[#EA0A2C] py-3 text-sm font-semibold text-white transition-colors duration-200 hover:bg-[#C80825] focus:outline-none focus:ring-2 focus:ring-[#EA0A2C]/40 focus:ring-offset-2 active:bg-[#A60620] disabled:cursor-not-allowed disabled:bg-gray-300"
                disabled={isSubmitting || locked}
              >
                {isSubmitting ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Memproses…
                  </>
                ) : locked ? (
                  "Terkunci sementara"
                ) : (
                  <>
                    Masuk
                    <svg className="transition-transform duration-200 group-hover:translate-x-0.5" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M5 12h14" /><path d="M13 6l6 6-6 6" />
                    </svg>
                  </>
                )}
              </button>
            </form>

            {/* Security notice */}
            <p className="mt-8 border-t border-gray-100 pt-6 text-xs leading-relaxed text-gray-400">
              Sistem terbatas. Akses hanya untuk personel IndiHome by Telkomsel yang berwenang; seluruh aktivitas
              dicatat dan dipantau.
            </p>
          </div>
        </div>
      </div>

      {/* ───────────── Recovery modal ───────────── */}
      {showRecovery && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 px-4"
          onClick={() => setShowRecovery(false)}
        >
          <div
            className="w-full max-w-md rounded-xl bg-white p-7 shadow-2xl ring-1 ring-black/5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-5 flex items-center justify-between">
              <h3 className="text-lg font-bold text-gray-900">Pemulihan akun</h3>
              <button
                onClick={() => setShowRecovery(false)}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                aria-label="Tutup"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <p className="mb-1 font-semibold text-gray-900">Opsi 1 — Reset oleh admin</p>
                <p className="text-xs leading-relaxed text-gray-500">
                  Hubungi Administrator Sistem untuk mereset kata sandi Anda lewat panel Manajemen Pengguna.
                  Admin dapat memberikan kata sandi sementara yang baru.
                </p>
              </div>

              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <p className="mb-1 font-semibold text-gray-900">Opsi 2 — Inisialisasi ulang akun</p>
                <p className="text-xs leading-relaxed text-gray-500">
                  Jika akun admin sendiri terkunci, operator sistem yang memiliki{" "}
                  <code className="rounded bg-gray-200 px-1.5 py-0.5 font-mono text-[11px] text-gray-700">SEED_TOKEN</code>{" "}
                  dapat menginisialisasi ulang akun admin lewat endpoint seed API.
                </p>
              </div>

              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <p className="mb-1 font-semibold text-amber-800">Catatan keamanan</p>
                <p className="text-xs leading-relaxed text-amber-700">
                  Demi keamanan, reset kata sandi mandiri tidak tersedia. Semua perubahan kredensial
                  memerlukan verifikasi administrator untuk mencegah akses tidak sah.
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowRecovery(false)}
              className="mt-6 w-full rounded-lg bg-[#EA0A2C] py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#C80825] active:bg-[#A60620]"
            >
              Mengerti
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
