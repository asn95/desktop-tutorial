import type { ReactNode } from "react";
import { useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { Link, useLocation } from "react-router-dom";

const tabs = [
  { name: "DASHBOARD", path: "/dashboard" },
  { name: "ANALYTICS", path: "/analytics" },
  { name: "USER MANAGEMENT", path: "/users" },
  { name: "TARGETS", path: "/targets" },
];

export function AppShell({
  children,
}: {
  children: ReactNode;
  activeTab?: string;
}) {
  const { logout } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white font-sans text-[#1a1c1e] overflow-x-hidden">
      {/* Official Header */}
      <header className="mx-auto w-full max-w-[1400px] sm:border-x border-t border-black px-4 py-4 sm:px-8 sm:py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <svg width="32" height="32" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="sm:w-9 sm:h-9">
              {/* Radar base triangle */}
              <path d="M20 4 L4 36 L36 36 Z" fill="#1a1c1e" stroke="#1a1c1e" strokeWidth="1.5" strokeLinejoin="round" />
              {/* Signal waves */}
              <path d="M28 18 C30 20 30 24 28 26" stroke="#e11d48" strokeWidth="2.5" strokeLinecap="round" fill="none" />
              <path d="M32 14 C36 18 36 28 32 32" stroke="#e11d48" strokeWidth="2.5" strokeLinecap="round" fill="none" />
              {/* Center dot */}
              <circle cx="20" cy="26" r="2.5" fill="white" />
            </svg>
            <div className="text-2xl sm:text-3xl font-black tracking-tighter">
              <span className="text-[#e11d48]">C</span><span>3MR</span>
            </div>
          </div>
          <div className="hidden sm:block text-[10px] font-black uppercase tracking-[0.2em] text-[#1a1c1e]">
            Official Management Portal
          </div>
          {/* Hamburger — mobile only */}
          <button
            className="sm:hidden flex flex-col gap-[5px] p-1"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
          >
            <span className={`block w-6 h-[2px] bg-[#1a1c1e] transition-transform origin-center ${menuOpen ? "rotate-45 translate-y-[7px]" : ""}`} />
            <span className={`block w-6 h-[2px] bg-[#1a1c1e] transition-opacity ${menuOpen ? "opacity-0" : ""}`} />
            <span className={`block w-6 h-[2px] bg-[#1a1c1e] transition-transform origin-center ${menuOpen ? "-rotate-45 -translate-y-[7px]" : ""}`} />
          </button>
        </div>
      </header>

      {/* Navigation — desktop: horizontal tabs; mobile: dropdown */}
      <nav className="mx-auto w-full max-w-[1400px] sm:border-x border-y border-black">
        {/* Desktop nav */}
        <div className="hidden sm:flex px-4">
          {tabs.map((tab) => {
            const isActive = location.pathname === tab.path;
            return (
              <Link
                key={tab.path}
                to={tab.path}
                className={`relative px-6 py-5 text-[11px] font-black tracking-widest transition hover:text-[#e11d48] ${
                  isActive ? "text-[#1a1c1e]" : "text-[#5e6671]"
                }`}
              >
                {tab.name}
                {isActive && (
                  <div className="absolute bottom-[-1px] left-0 h-[3px] w-full bg-[#e11d48]" />
                )}
              </Link>
            );
          })}
          <div className="ml-auto flex items-center px-4">
            <button
              onClick={logout}
              className="text-[10px] font-black uppercase tracking-widest text-red-600 hover:underline"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Mobile nav — shown when hamburger is open */}
        {menuOpen && (
          <div className="sm:hidden flex flex-col border-t border-black">
            {tabs.map((tab) => {
              const isActive = location.pathname === tab.path;
              return (
                <Link
                  key={tab.path}
                  to={tab.path}
                  onClick={() => setMenuOpen(false)}
                  className={`px-6 py-4 text-[11px] font-black tracking-widest border-b border-slate-100 transition hover:text-[#e11d48] ${
                    isActive ? "text-[#1a1c1e] bg-red-50" : "text-[#5e6671]"
                  }`}
                >
                  {tab.name}
                </Link>
              );
            })}
            <button
              onClick={() => { setMenuOpen(false); logout(); }}
              className="px-6 py-4 text-left text-[11px] font-black tracking-widest text-red-600 hover:underline"
            >
              LOGOUT
            </button>
          </div>
        )}
      </nav>

      <main className="mx-auto w-full max-w-[1400px] sm:border-x border-b border-black p-4 sm:p-8">
        {children}

        <footer className="mt-12 sm:mt-20 border-t border-slate-100 pt-8 text-[10px] font-medium text-slate-400 italic">
          Generated by C3MR System - Confidential Document
        </footer>
      </main>
    </div>
  );
}
