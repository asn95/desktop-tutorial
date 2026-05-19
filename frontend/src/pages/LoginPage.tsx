import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      setIsSubmitting(true);
      await login({ email, password });
      navigate(redirectPath, { replace: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to login. Please try again.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

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
            <label htmlFor="email" className="text-[11px] font-black uppercase tracking-wider text-[#1a1c1e]">
              Corporate Email
            </label>
            <input
              id="email"
              type="email"
              required
              className="w-full rounded-lg border border-[#e2e8f0] bg-[#f8fafc] px-4 py-3 text-sm outline-none transition focus:border-[#1a1c1e]"
              placeholder="auzarahman@c3mr.id"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-[11px] font-black uppercase tracking-wider text-[#1a1c1e]">
              Secure Password
            </label>
            <input
              id="password"
              type="password"
              required
              className="w-full rounded-lg border border-[#e2e8f0] bg-[#f8fafc] px-4 py-3 text-sm outline-none transition focus:border-[#1a1c1e]"
              placeholder="••••••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          <div className="flex items-center justify-between py-1">
            <label className="flex items-center gap-2 text-xs font-bold text-[#5e6671]">
              <input type="checkbox" className="h-4 w-4 rounded border-[#e2e8f0]" />
              Remember Device
            </label>
            <button type="button" className="text-xs font-black text-[#2563eb] hover:underline">
              Recovery Options
            </button>
          </div>

          {error ? (
            <div className="rounded-lg bg-red-50 p-3 text-center text-xs font-bold text-red-600">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            className="w-full rounded-lg bg-[#0f172a] py-4 text-sm font-black uppercase tracking-widest text-white transition hover:bg-[#1e293b] active:scale-[0.99] disabled:bg-[#94a3b8]"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Processing..." : "Authorize & Sign In"}
          </button>
        </form>

        <div className="mt-10 border-t border-[#f1f5f9] pt-8">
          <p className="text-center text-[10px] font-bold leading-relaxed uppercase tracking-wider text-[#94a3b8]">
            <span className="text-[#64748b]">System Warning:</span> This is a restricted government-grade monitoring system. All activities are logged under Presidential Regulation No. 95/2018.
          </p>
        </div>
      </div>

      <footer className="mt-8 text-center text-[11px] font-bold text-[#64748b]">
        © 2026 President University — C3MR Operational Division
      </footer>
    </div>
  );
}
