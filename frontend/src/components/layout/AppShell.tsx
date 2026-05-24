import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../contexts/ThemeContext";
import { apiClient } from "../../lib/apiClient";
import { Link, useLocation } from "react-router-dom";

const tabs = [
  { name: "DASHBOARD", path: "/dashboard" },
  { name: "ANALYTICS", path: "/analytics" },
  { name: "USER MANAGEMENT", path: "/users" },
  { name: "TARGETS", path: "/targets" },
  { name: "AUDIT LOG", path: "/audit" },
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
  const [maintMsg, setMaintMsg] = useState("System is under maintenance. Please try again later.");
  const [maintToggling, setMaintToggling] = useState(false);
  const [showMaintModal, setShowMaintModal] = useState(false);
  const [maintCustomMsg, setMaintCustomMsg] = useState("");

  // Fetch maintenance status on mount
  useEffect(() => {
    apiClient.get("/admin/maintenance")
      .then(res => {
        setMaintenance(res.data.enabled);
        setMaintMsg(res.data.message);
        setMaintCustomMsg(res.data.message);
      })
      .catch(() => {});
  }, []);

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
      setPwMsg({ ok: true, text: "Password changed successfully." });
      setCurPw("");
      setNewPw("");
    } catch (err: any) {
      setPwMsg({ ok: false, text: err.response?.data?.detail || "Failed to change password." });
    } finally {
      setPwLoading(false);
    }
  }

  return (
    <div className={`min-h-screen font-sans overflow-x-hidden ${dark ? "bg-[#0f1117] text-slate-200" : "bg-white text-[#1a1c1e]"}`}>
      {/* Maintenance Banner */}
      {maintenance && (
        <div className="bg-amber-500 text-black px-4 py-2 text-center text-[10px] font-black uppercase tracking-widest">
          Maintenance Mode Active — Only managers can access the system
        </div>
      )}

      {/* Official Header */}
      <header className={`mx-auto w-full max-w-[1400px] sm:border-x border-t px-4 py-4 sm:px-8 sm:py-6 ${dark ? "border-slate-700" : "border-black"}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <svg width="32" height="32" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="sm:w-9 sm:h-9">
              <path d="M20 4 L4 36 L36 36 Z" fill={dark ? "#e11d48" : "#1a1c1e"} stroke={dark ? "#e11d48" : "#1a1c1e"} strokeWidth="1.5" strokeLinejoin="round" />
              <path d="M28 18 C30 20 30 24 28 26" stroke={dark ? "white" : "#e11d48"} strokeWidth="2.5" strokeLinecap="round" fill="none" />
              <path d="M32 14 C36 18 36 28 32 32" stroke={dark ? "white" : "#e11d48"} strokeWidth="2.5" strokeLinecap="round" fill="none" />
              <circle cx="20" cy="26" r="2.5" fill="white" />
            </svg>
            <div className="text-2xl sm:text-3xl font-black tracking-tighter">
              <span className="text-[#e11d48]">C</span><span>3MR</span>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-4">
            <span className={`text-[10px] font-black uppercase tracking-[0.2em] ${dark ? "text-slate-400" : "text-[#1a1c1e]"}`}>
              Official Management Portal
            </span>
            <button onClick={toggle} className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 border transition ${dark ? "border-slate-600 text-slate-300 hover:bg-slate-800" : "border-black hover:bg-slate-100"}`}>
              {dark ? "Light" : "Dark"}
            </button>
          </div>
          {/* Hamburger — mobile only */}
          <div className="flex sm:hidden items-center gap-3">
            <button onClick={toggle} className={`text-[9px] font-black uppercase tracking-widest px-2 py-1 border ${dark ? "border-slate-600 text-slate-300" : "border-black"}`}>
              {dark ? "LT" : "DK"}
            </button>
            <button
              className="flex flex-col gap-[5px] p-1"
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label="Toggle menu"
            >
              <span className={`block w-6 h-[2px] transition-transform origin-center ${dark ? "bg-slate-200" : "bg-[#1a1c1e]"} ${menuOpen ? "rotate-45 translate-y-[7px]" : ""}`} />
              <span className={`block w-6 h-[2px] transition-opacity ${dark ? "bg-slate-200" : "bg-[#1a1c1e]"} ${menuOpen ? "opacity-0" : ""}`} />
              <span className={`block w-6 h-[2px] transition-transform origin-center ${dark ? "bg-slate-200" : "bg-[#1a1c1e]"} ${menuOpen ? "-rotate-45 -translate-y-[7px]" : ""}`} />
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className={`mx-auto w-full max-w-[1400px] sm:border-x border-y ${dark ? "border-slate-700" : "border-black"}`}>
        {/* Desktop nav */}
        <div className="hidden sm:flex px-4">
          {tabs.map((tab) => {
            const isActive = location.pathname === tab.path;
            return (
              <Link
                key={tab.path}
                to={tab.path}
                className={`relative px-6 py-5 text-[11px] font-black tracking-widest transition hover:text-[#e11d48] ${
                  isActive ? (dark ? "text-white" : "text-[#1a1c1e]") : (dark ? "text-slate-500" : "text-[#5e6671]")
                }`}
              >
                {tab.name}
                {isActive && (
                  <div className="absolute bottom-[-1px] left-0 h-[3px] w-full bg-[#e11d48]" />
                )}
              </Link>
            );
          })}
          <div className="ml-auto flex items-center gap-4 px-4">
            <button
              onClick={() => { setMaintCustomMsg(maintMsg); setShowMaintModal(true); }}
              className={`text-[10px] font-black uppercase tracking-widest hover:underline ${maintenance ? "text-amber-500" : dark ? "text-slate-400" : "text-slate-500"}`}
            >
              {maintenance ? "Maint: ON" : "Maint"}
            </button>
            <button
              onClick={() => setShowPwModal(true)}
              className={`text-[10px] font-black uppercase tracking-widest hover:underline ${dark ? "text-slate-400" : "text-slate-500"}`}
            >
              Password
            </button>
            <button
              onClick={logout}
              className="text-[10px] font-black uppercase tracking-widest text-red-600 hover:underline"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Mobile nav */}
        {menuOpen && (
          <div className={`sm:hidden flex flex-col border-t ${dark ? "border-slate-700" : "border-black"}`}>
            {tabs.map((tab) => {
              const isActive = location.pathname === tab.path;
              return (
                <Link
                  key={tab.path}
                  to={tab.path}
                  onClick={() => setMenuOpen(false)}
                  className={`px-6 py-4 text-[11px] font-black tracking-widest border-b transition hover:text-[#e11d48] ${
                    dark ? "border-slate-800" : "border-slate-100"
                  } ${
                    isActive ? (dark ? "text-white bg-slate-800" : "text-[#1a1c1e] bg-red-50") : (dark ? "text-slate-500" : "text-[#5e6671]")
                  }`}
                >
                  {tab.name}
                </Link>
              );
            })}
            <button
              onClick={() => { setMenuOpen(false); setMaintCustomMsg(maintMsg); setShowMaintModal(true); }}
              className={`px-6 py-4 text-left text-[11px] font-black tracking-widest border-b hover:underline ${maintenance ? "text-amber-500 border-amber-500/20" : dark ? "border-slate-800 text-slate-400" : "border-slate-100 text-slate-500"}`}
            >
              {maintenance ? "MAINTENANCE: ON" : "MAINTENANCE MODE"}
            </button>
            <button
              onClick={() => { setMenuOpen(false); setShowPwModal(true); }}
              className={`px-6 py-4 text-left text-[11px] font-black tracking-widest border-b hover:underline ${dark ? "border-slate-800 text-slate-400" : "border-slate-100 text-slate-500"}`}
            >
              CHANGE PASSWORD
            </button>
            <button
              onClick={() => { setMenuOpen(false); logout(); }}
              className="px-6 py-4 text-left text-[11px] font-black tracking-widest text-red-600 hover:underline"
            >
              LOGOUT
            </button>
          </div>
        )}
      </nav>

      <main className={`mx-auto w-full max-w-[1400px] sm:border-x border-b p-4 sm:p-8 ${dark ? "border-slate-700" : "border-black"}`}>
        {children}

        <footer className={`mt-12 sm:mt-20 border-t pt-8 text-[10px] font-medium italic ${dark ? "border-slate-800 text-slate-600" : "border-slate-100 text-slate-400"}`}>
          Generated by C3MR System - Confidential Document
        </footer>
      </main>

      {/* Maintenance Mode Modal */}
      {showMaintModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowMaintModal(false)}>
          <div
            onClick={e => e.stopPropagation()}
            className={`w-full max-w-sm mx-4 p-6 space-y-5 border ${dark ? "bg-slate-800 border-slate-600" : "bg-white border-black"}`}
          >
            <div>
              <h2 className={`text-xs font-black uppercase tracking-widest ${dark ? "text-white" : ""}`}>Maintenance Mode</h2>
              <p className={`text-[10px] mt-2 ${dark ? "text-slate-400" : "text-slate-500"}`}>
                {maintenance
                  ? "System is currently in maintenance mode. Officers and external users cannot access the API."
                  : "Enable maintenance mode to block all non-manager access to the system."
                }
              </p>
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">Message shown to users</label>
              <input
                value={maintCustomMsg}
                onChange={e => setMaintCustomMsg(e.target.value)}
                placeholder="System is under maintenance..."
                className={`w-full border-b bg-transparent px-0 py-2 text-sm font-bold outline-none focus:border-b-2 ${dark ? "border-slate-600 text-white" : "border-black"}`}
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleToggleMaintenance}
                disabled={maintToggling}
                className={`flex-1 py-2.5 text-[10px] font-black uppercase tracking-widest disabled:opacity-30 ${
                  maintenance
                    ? "bg-green-600 text-white hover:bg-green-700"
                    : "bg-amber-500 text-black hover:bg-amber-600"
                }`}
              >
                {maintToggling ? "Updating..." : maintenance ? "Disable Maintenance" : "Enable Maintenance"}
              </button>
              <button
                type="button"
                onClick={() => setShowMaintModal(false)}
                className={`flex-1 border py-2.5 text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 ${dark ? "border-slate-600 text-slate-300 hover:bg-slate-700" : "border-black"}`}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showPwModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowPwModal(false)}>
          <form
            onSubmit={handleChangePw}
            onClick={e => e.stopPropagation()}
            className={`w-full max-w-xs mx-4 p-6 space-y-5 border ${dark ? "bg-slate-800 border-slate-600" : "bg-white border-black"}`}
          >
            <h2 className={`text-xs font-black uppercase tracking-widest ${dark ? "text-white" : ""}`}>Change Password</h2>
            <div className="space-y-1.5">
              <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">Current Password</label>
              <input
                type="password"
                autoFocus
                value={curPw}
                onChange={e => setCurPw(e.target.value)}
                className={`w-full border-b bg-transparent px-0 py-2 text-sm font-bold outline-none focus:border-b-2 ${dark ? "border-slate-600 text-white" : "border-black"}`}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">New Password</label>
              <input
                type="password"
                value={newPw}
                onChange={e => setNewPw(e.target.value)}
                className={`w-full border-b bg-transparent px-0 py-2 text-sm font-bold outline-none focus:border-b-2 ${dark ? "border-slate-600 text-white" : "border-black"}`}
              />
            </div>
            {pwMsg && (
              <p className={`text-[10px] font-bold ${pwMsg.ok ? "text-green-600" : "text-red-600"}`}>{pwMsg.text}</p>
            )}
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={!curPw || !newPw || pwLoading}
                className="flex-1 bg-black text-white py-2.5 text-[10px] font-black uppercase tracking-widest hover:bg-slate-800 disabled:opacity-30 dark:bg-white dark:text-black dark:hover:bg-slate-200"
              >
                {pwLoading ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={() => { setShowPwModal(false); setPwMsg(null); setCurPw(""); setNewPw(""); }}
                className={`flex-1 border py-2.5 text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 ${dark ? "border-slate-600 text-slate-300 hover:bg-slate-700" : "border-black"}`}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
