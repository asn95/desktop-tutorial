import { useEffect, useRef, useState } from "react";
import type { PeriodInfo } from "../../types/dashboard";
import { formatPeriodLabel } from "../../lib/format";

const EASE = "ease-[cubic-bezier(0.32,0.72,0,1)]";

interface PeriodSelectorProps {
  periods: PeriodInfo[];
  value: string;
  onChange: (period: string) => void;
}

export function PeriodSelector({ periods, value, onChange }: PeriodSelectorProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const totalAll = periods.reduce((sum, p) => sum + p.total, 0);
  const options = [
    ...periods.map((p) => ({ key: p.period, label: formatPeriodLabel(p.period), total: p.total })),
    { key: "all", label: "Semua Periode", total: totalAll },
  ];

  return (
    <div ref={rootRef} className="relative w-fit">
      {/* Floating pill trigger */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`group flex items-center gap-2.5 rounded-full bg-white py-1.5 pl-1.5 pr-4 ring-1 ring-black/5 shadow-[0_2px_16px_-6px_rgba(16,24,40,0.18)] transition-all duration-500 ${EASE} hover:shadow-[0_6px_24px_-8px_rgba(16,24,40,0.24)] active:scale-[0.98] dark:bg-slate-800 dark:ring-white/10`}
      >
        <span className={`flex h-8 w-8 items-center justify-center rounded-full bg-red-50 text-[#E81E28] transition-transform duration-500 ${EASE} group-hover:scale-105 dark:bg-red-500/10`}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" className="h-4 w-4">
            <rect x="3.5" y="5" width="17" height="15.5" rx="3" />
            <path d="M3.5 9.5h17M8 3v3.5M16 3v3.5" />
          </svg>
        </span>
        <span className="flex flex-col items-start leading-none">
          <span className="text-[9px] font-medium uppercase tracking-[0.2em] text-gray-400 dark:text-slate-500">Periode</span>
          <span className="mt-1 text-sm font-semibold tracking-tight text-gray-900 dark:text-white">{formatPeriodLabel(value)}</span>
        </span>
        <svg
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"
          className={`ml-1 h-3.5 w-3.5 text-gray-400 transition-transform duration-500 ${EASE} ${open ? "rotate-180" : ""}`}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {/* Dropdown — double-bezel card, always mounted for fluid exit */}
      <div className={`absolute right-0 z-40 mt-2.5 w-64 origin-top-right ${open ? "" : "pointer-events-none"}`}>
        <div
          className={`rounded-[1.25rem] bg-gray-50/90 p-1.5 ring-1 ring-black/5 shadow-[0_24px_60px_-20px_rgba(16,24,40,0.28)] transition-all duration-500 ${EASE} dark:bg-slate-900/90 dark:ring-white/10 ${
            open ? "translate-y-0 scale-100 opacity-100" : "-translate-y-2 scale-[0.97] opacity-0"
          }`}
        >
          <div className="rounded-[calc(1.25rem-0.375rem)] bg-white p-1.5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)] dark:bg-slate-800">
            <p className="px-3 pb-1.5 pt-2.5 text-[9px] font-medium uppercase tracking-[0.2em] text-gray-400 dark:text-slate-500">
              Periode Data
            </p>
            <div className="max-h-72 overflow-y-auto">
              {options.map((opt, i) => {
                const isActive = value === opt.key;
                const isAll = opt.key === "all";
                return (
                  <div key={opt.key}>
                    {isAll && <div className="mx-3 my-1 h-px bg-gray-100 dark:bg-slate-700" />}
                    <button
                      type="button"
                      onClick={() => { onChange(opt.key); setOpen(false); }}
                      style={{ transitionDelay: open ? `${50 + i * 35}ms` : "0ms" }}
                      className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left transition-all duration-500 ${EASE} ${
                        open ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0"
                      } ${isActive ? "bg-red-50/80 dark:bg-red-500/10" : "hover:bg-gray-50 dark:hover:bg-slate-700/50"}`}
                    >
                      <span className="flex items-center gap-2.5">
                        <span className={`h-1.5 w-1.5 rounded-full transition-colors duration-500 ${isActive ? "bg-[#E81E28]" : "bg-gray-200 dark:bg-slate-600"}`} />
                        <span className={`text-sm ${isActive ? "font-semibold text-[#E81E28]" : "font-medium text-gray-700 dark:text-slate-200"}`}>
                          {opt.label}
                        </span>
                      </span>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        isActive ? "bg-white text-[#E81E28] dark:bg-slate-800" : "bg-gray-50 text-gray-400 dark:bg-slate-700 dark:text-slate-400"
                      }`}>
                        {opt.total}
                      </span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
