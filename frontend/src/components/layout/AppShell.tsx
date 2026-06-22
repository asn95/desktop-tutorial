import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../contexts/ThemeContext";
import { apiClient } from "../../lib/apiClient";
import { Link, useLocation } from "react-router-dom";
import telkomLogo from "../../assets/telkom-logo.png";

type IconProps = { className?: string };
const I = {
  dashboard: (p: IconProps) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  ),
  analytics: (p: IconProps) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M3 3v18h18" /><path d="M7 14l3-4 3 3 4-6" />
    </svg>
  ),
  users: (p: IconProps) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <circle cx="9" cy="8" r="3" /><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" /><path d="M16 5.2a3 3 0 0 1 0 5.6M18 20c0-2.4-1-4.5-2.5-5.8" />
    </svg>
  ),
  targets: (p: IconProps) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3.5" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
    </svg>
  ),
  audit: (p: IconProps) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <rect x="5" y="3" width="14" height="18" rx="2" /><path d="M9 8h6M9 12h6M9 16h4" />
    </svg>
  ),
  assistant: (p: IconProps) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M12 3l1.7 4.3L18 9l-4.3 1.7L12 15l-1.7-4.3L6 9l4.3-1.7z" /><path d="M18.5 14.5l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z" />
    </svg>
  ),
};

const tabs = [
  { name: "Dasbor", path: "/dashboard", icon: I.dashboard },
  { name: "Analitik", path: "/analytics", icon: I.analytics },
  { name: "Manajemen Pengguna", path: "/users", icon: I.users },
  { name: "Target", path: "/targets", icon: I.targets },
  { name: "Log Audit", path: "/audit", icon: I.audit },
  { name: "Asisten AI", path: "/assistant", icon: I.assistant },
];

export function AppShell({
  children,
}: {
  children: ReactNode;
  activeTab?: string;
}) {
  const { logout } = useAuth();
  const { dark, toggle } = useTheme();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [showPwModal, setShowPwModal] = useState(false);
  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [pwLoading, setPwLoading] = useState(false);
  const [maintenance, setMaintenance] = useState(false);
  const [maintMsg, setMaintMsg] = useState("Sistem sedang dalam pemeliharaan. Silakan coba lagi nanti.");
  const [maintToggling, setMaintToggling] = useState(false);
  const [showMaintModal, setShowMaintModal] = useState(false);
  const [maintCustomMsg, setMaintCustomMsg] = useState("");

  useEffect(() => {
    apiClient.get("/admin/maintenance")
      .then(res => {
        setMaintenance(res.data.enabled);
        setMaintMsg(res.data.message);
        setMaintCustomMsg(res.data.message);
      })
      .catch(() => {});
  }, []);

  // close mobile drawer on route change
  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  async function handleToggleMaintenance() {
    setMaintToggling(true);
    try {
      const res = await apiClient.post("/admin/maintenance", {
        enabled: !maintenance,
        message: maintCustomMsg || undefined,
      });
      setMaintenance(res.data.enabled);
      setMaintMsg(res.data.message);
      setShowMaintModal(false);
    } catch {
      alert("Failed to toggle maintenance mode.");
    } finally {
      setMaintToggling(false);
    }
  }

  async function handleChangePw(e: React.FormEvent) {
    e.preventDefault();
    setPwLoading(true);
    setPwMsg(null);
    try {
      await apiClient.post("/auth/change-password", { current_password: curPw, new_password: newPw });
      setPwMsg({ ok: true, text: "Kata sandi berhasil diubah." });
      setCurPw("");
      setNewPw("");
    } catch (err: any) {
      setPwMsg({ ok: false, text: err.response?.data?.detail || "Gagal mengubah kata sandi." });
    } finally {
      setPwLoading(false);
    }
  }

  const sidebar = (
    <div className="flex h-full flex-col">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-6 py-6">
        <img src={telkomLogo} alt="Telkom Indonesia" className="h-9 w-9 object-contain" />
        <div className="leading-tight">
          <div className="text-lg font-extrabold tracking-tight"><span className="text-[#E81E28]">C</span>3MR</div>
          <div className={`text-[10px] font-medium ${dark ? "text-slate-500" : "text-gray-400"}`}>Portal Manajemen</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 px-3 py-2">
        {tabs.map((tab) => {
          const isActive = location.pathname === tab.path;
          const Icon = tab.icon;
          return (
            <Link
              key={tab.path}
              to={tab.path}
              className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-[#E81E28]/10 text-[#E81E28]"
                  : dark
                  ? "text-slate-400 hover:bg-slate-800/70 hover:text-slate-100"
                  : "text-gray-500 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <Icon className={`h-[18px] w-[18px] transition-transform duration-200 ${isActive ? "" : "group-hover:scale-110"}`} />
              {tab.name}
            </Link>
          );
        })}
      </nav>

      {/* Actions */}
      <div className={`mt-auto space-y-1 border-t px-3 py-4 ${dark ? "border-slate-800" : "border-gray-100"}`}>
        <button onClick={toggle} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${dark ? "text-slate-400 hover:bg-slate-800/70" : "text-gray-500 hover:bg-gray-100"}`}>
          {dark ? "Mode Terang" : "Mode Gelap"}
        </button>
        <button onClick={() => { setMaintCustomMsg(maintMsg); setShowMaintModal(true); }} className={`flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${maintenance ? "text-amber-600 hover:bg-amber-50" : dark ? "text-slate-400 hover:bg-slate-800/70" : "text-gray-500 hover:bg-gray-100"}`}>
          Pemeliharaan
          {maintenance && <span className="h-2 w-2 rounded-full bg-amber-500" />}
        </button>
        <button onClick={() => setShowPwModal(true)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${dark ? "text-slate-400 hover:bg-slate-800/70" : "text-gray-500 hover:bg-gray-100"}`}>
          Ubah Kata Sandi
        </button>
        <button onClick={logout} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-[#E81E28] transition-colors hover:bg-red-50">
          Keluar
        </button>
      </div>
    </div>
  );

  return (
    <div className={`min-h-screen font-sans ${dark ? "bg-[#0f1117] text-slate-200" : "bg-[#f4f5f7] text-gray-900"}`}>
      {maintenance && (
        <div className="relative z-50 bg-amber-500 px-4 py-2 text-center text-xs font-semibold text-black">
          Mode pemeliharaan aktif — hanya manajer yang dapat mengakses sistem
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 hidden w-64 lg:block ${dark ? "bg-[#13151d]" : "bg-white shadow-[1px_0_24px_-12px_rgba(16,24,40,0.12)]"} ${maintenance ? "lg:top-[36px]" : ""}`}>
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      <div className={`fixed inset-0 z-50 lg:hidden ${menuOpen ? "" : "pointer-events-none"}`}>
        <div className={`absolute inset-0 bg-gray-900/40 transition-opacity duration-300 ${menuOpen ? "opacity-100" : "opacity-0"}`} onClick={() => setMenuOpen(false)} />
        <aside className={`absolute inset-y-0 left-0 w-72 transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] ${dark ? "bg-[#13151d]" : "bg-white"} ${menuOpen ? "translate-x-0" : "-translate-x-full"}`}>
          {sidebar}
        </aside>
      </div>

      {/* Content */}
      <div className="lg:pl-64">
        {/* Mobile top bar */}
        <header className={`sticky top-0 z-30 flex items-center justify-between border-b px-4 py-3 backdrop-blur lg:hidden ${dark ? "border-slate-800 bg-[#0f1117]/85" : "border-gray-200 bg-white/85"}`}>
          <div className="flex items-center gap-2">
            <img src={telkomLogo} alt="Telkom" className="h-7 w-7 object-contain" />
            <span className="text-lg font-extrabold tracking-tight"><span className="text-[#E81E28]">C</span>3MR</span>
          </div>
          <button className="flex flex-col gap-[5px] p-1" onClick={() => setMenuOpen(true)} aria-label="Buka menu">
            <span className={`block h-[2px] w-6 ${dark ? "bg-slate-200" : "bg-gray-900"}`} />
            <span className={`block h-[2px] w-6 ${dark ? "bg-slate-200" : "bg-gray-900"}`} />
            <span className={`block h-[2px] w-6 ${dark ? "bg-slate-200" : "bg-gray-900"}`} />
          </button>
        </header>

        <main className="mx-auto max-w-6xl px-5 py-8 sm:px-8 lg:py-10">
          {children}
          <footer className={`mt-16 pt-6 text-xs ${dark ? "text-slate-600" : "text-gray-400"}`}>
            C3MR — PT Telkom Indonesia (Persero) Tbk · Rahasia
          </footer>
        </main>
      </div>

      {/* Maintenance Mode Modal */}
      {showMaintModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-gray-900/40 px-4" onClick={() => setShowMaintModal(false)}>
          <div onClick={e => e.stopPropagation()} className={`w-full max-w-md rounded-2xl p-6 shadow-2xl ${dark ? "bg-[#1a1d27]" : "bg-white"}`}>
            <h2 className="text-lg font-bold text-gray-900">Mode Pemeliharaan</h2>
            <p className="mt-1.5 text-sm text-gray-500">
              {maintenance
                ? "Sistem sedang dalam mode pemeliharaan. Petugas dan pengguna eksternal tidak dapat mengakses API."
                : "Aktifkan mode pemeliharaan untuk memblokir semua akses non-manajer ke sistem."}
            </p>
            <div className="mt-5 space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">Pesan yang ditampilkan ke pengguna</label>
              <input value={maintCustomMsg} onChange={e => setMaintCustomMsg(e.target.value)} placeholder="Sistem sedang dalam pemeliharaan…"
                className="w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 outline-none transition focus:border-[#E81E28] focus:ring-2 focus:ring-[#E81E28]/20" />
            </div>
            <div className="mt-6 flex gap-3">
              <button onClick={handleToggleMaintenance} disabled={maintToggling}
                className={`flex-1 rounded-lg py-2.5 text-sm font-semibold text-white transition-colors disabled:opacity-40 ${maintenance ? "bg-emerald-600 hover:bg-emerald-700" : "bg-amber-500 text-black hover:bg-amber-600"}`}>
                {maintToggling ? "Memperbarui…" : maintenance ? "Nonaktifkan pemeliharaan" : "Aktifkan pemeliharaan"}
              </button>
              <button type="button" onClick={() => setShowMaintModal(false)}
                className={`flex-1 rounded-lg border py-2.5 text-sm font-medium transition-colors ${dark ? "border-slate-600 text-slate-300 hover:bg-slate-800" : "border-gray-300 text-gray-700 hover:bg-gray-50"}`}>
                Batal
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showPwModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-gray-900/40 px-4" onClick={() => setShowPwModal(false)}>
          <form onSubmit={handleChangePw} onClick={e => e.stopPropagation()} className={`w-full max-w-sm rounded-2xl p-6 shadow-2xl ${dark ? "bg-[#1a1d27]" : "bg-white"}`}>
            <h2 className="text-lg font-bold text-gray-900">Ubah Kata Sandi</h2>
            <div className="mt-5 space-y-4">
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-gray-700">Kata sandi saat ini</label>
                <input type="password" autoFocus value={curPw} onChange={e => setCurPw(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 outline-none transition focus:border-[#E81E28] focus:ring-2 focus:ring-[#E81E28]/20" />
              </div>
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-gray-700">Kata sandi baru</label>
                <input type="password" value={newPw} onChange={e => setNewPw(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 outline-none transition focus:border-[#E81E28] focus:ring-2 focus:ring-[#E81E28]/20" />
              </div>
            </div>
            {pwMsg && <p className={`mt-3 text-sm font-medium ${pwMsg.ok ? "text-emerald-600" : "text-[#E81E28]"}`}>{pwMsg.text}</p>}
            <div className="mt-6 flex gap-3">
              <button type="submit" disabled={!curPw || !newPw || pwLoading}
                className="flex-1 rounded-lg bg-[#E81E28] py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#c8161f] disabled:opacity-40">
                {pwLoading ? "Menyimpan…" : "Simpan"}
              </button>
              <button type="button" onClick={() => { setShowPwModal(false); setPwMsg(null); setCurPw(""); setNewPw(""); }}
                className={`flex-1 rounded-lg border py-2.5 text-sm font-medium transition-colors ${dark ? "border-slate-600 text-slate-300 hover:bg-slate-800" : "border-gray-300 text-gray-700 hover:bg-gray-50"}`}>
                Batal
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
