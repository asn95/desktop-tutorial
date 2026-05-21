import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

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
      setError(`Too many failed attempts. Try again in ${lockCheck.remainingSec}s.`);
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
      const message = err instanceof Error ? err.message : "Unable to login. Please try again.";
      if (remaining > 0) {
        setError(`${message} (${remaining} attempt${remaining === 1 ? "" : "s"} remaining)`);
      } else {
        const lockCheck = isLockedOut();
        setLockoutSec(lockCheck.remainingSec);
        setError(`Account temporarily locked. Try again in ${lockCheck.remainingSec}s.`);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const locked = lockoutSec > 0 && isLockedOut().locked;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#e9eff6] px-4 font-sans">
      <div className="w-full max-w-[540px] rounded-xl bg-white p-12 shadow-2xl">
        {/* Branding */}
        <div className="mb-10 text-center">
          <div className="flex items-center justify-center gap-1 text-4xl font-black tracking-tighter text-[#1a1c1e]">
            <span className="text-[#e11d48]">C</span>
            <span>3MR</span>
          </div>
          <p className="mt-2 text-[11px] font-bold uppercase tracking-[0.25em] text-[#5e6671]">
            Integrated Management System
          </p>
        </div>

        {/* Portal Access Header */}
        <div className="mb-8 border-l-[6px] border-[#1a1c1e] pl-5">
          <h1 className="text-3xl font-bold tracking-tight text-[#1a1c1e]">Portal Access</h1>
          <p className="text-sm font-medium text-[#5e6671]">
            Provide credentials to establish session
          </p>
        </div>

        <form className="space-y-6" onSubmit={onSubmit}>
          <div className="space-y-2">
            <label htmlFor="username" className="text-[11px] font-black uppercase tracking-wider text-[#1a1c1e]">
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              autoComplete="username"
              className="w-full rounded-lg border border-[#e2e8f0] bg-[#f8fafc] px-4 py-3 text-sm outline-none transition focus:border-[#1a1c1e]"
              placeholder="admin"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              disabled={locked}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-[11px] font-black uppercase tracking-wider text-[#1a1c1e]">
              Secure Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                required
                autoComplete="current-password"
                className="w-full rounded-lg border border-[#e2e8f0] bg-[#f8fafc] px-4 py-3 pr-12 text-sm outline-none transition focus:border-[#1a1c1e]"
                placeholder="••••••••••••"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={locked}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94a3b8] hover:text-[#1a1c1e] transition"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                )}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between py-1">
            <label className="flex items-center gap-2 text-xs font-bold text-[#5e6671] cursor-pointer select-none">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-[#e2e8f0] accent-[#1a1c1e]"
                checked={rememberDevice}
                onChange={(e) => setRememberDevice(e.target.checked)}
              />
              Remember Device
            </label>
            <button
              type="button"
              className="text-xs font-black text-[#2563eb] hover:underline"
              onClick={() => setShowRecovery(true)}
            >
              Recovery Options
            </button>
          </div>

          {error ? (
            <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-center text-xs font-bold text-red-600">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline-block mr-1 -mt-0.5">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            className="w-full rounded-lg bg-[#0f172a] py-4 text-sm font-black uppercase tracking-widest text-white transition hover:bg-[#1e293b] active:scale-[0.99] disabled:bg-[#94a3b8] disabled:cursor-not-allowed"
            disabled={isSubmitting || locked}
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                Authenticating...
              </span>
            ) : locked ? (
              "Temporarily Locked"
            ) : (
              "Authorize & Sign In"
            )}
          </button>
        </form>

        <div className="mt-10 border-t border-[#f1f5f9] pt-8">
          <p className="text-center text-[10px] font-bold leading-relaxed uppercase tracking-wider text-[#94a3b8]">
            <span className="text-[#64748b]">System Warning:</span> This is a restricted government-grade monitoring system. All activities are logged under Presidential Regulation No. 95/2018.
          </p>
        </div>
      </div>

      <footer className="mt-8 text-center text-[11px] font-bold text-[#64748b]">
        &copy; 2026 President University &mdash; C3MR Operational Division
      </footer>

      {/* Recovery Options Modal */}
      {showRecovery && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4"
          onClick={() => setShowRecovery(false)}
        >
          <div
            className="w-full max-w-md rounded-xl bg-white p-8 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-xl font-bold text-[#1a1c1e]">Account Recovery</h2>
              <button
                onClick={() => setShowRecovery(false)}
                className="text-[#94a3b8] hover:text-[#1a1c1e] transition"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <div className="space-y-4 text-sm text-[#374151]">
              <div className="rounded-lg bg-[#f8fafc] border border-[#e2e8f0] p-4">
                <p className="font-black text-xs uppercase tracking-wider text-[#1a1c1e] mb-2">Option 1: Admin Reset</p>
                <p className="text-[#5e6671] text-xs leading-relaxed">
                  Contact your System Administrator to reset your password via the User Management panel. The admin can assign a new temporary password.
                </p>
              </div>

              <div className="rounded-lg bg-[#f8fafc] border border-[#e2e8f0] p-4">
                <p className="font-black text-xs uppercase tracking-wider text-[#1a1c1e] mb-2">Option 2: Re-seed Account</p>
                <p className="text-[#5e6671] text-xs leading-relaxed">
                  If the admin account itself is locked, a system operator with the <code className="bg-[#e2e8f0] px-1.5 py-0.5 rounded text-[10px] font-mono">SEED_TOKEN</code> can re-initialize the admin account via the API seed endpoint.
                </p>
              </div>

              <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
                <p className="font-black text-xs uppercase tracking-wider text-amber-800 mb-2">Security Notice</p>
                <p className="text-amber-700 text-xs leading-relaxed">
                  For security reasons, self-service password reset is not available. All credential changes require administrator verification to prevent unauthorized access.
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowRecovery(false)}
              className="mt-6 w-full rounded-lg bg-[#0f172a] py-3 text-xs font-black uppercase tracking-widest text-white hover:bg-[#1e293b] transition"
            >
              Understood
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
