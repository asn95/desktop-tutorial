import { useEffect, useRef, useState } from "react";
import type { PeriodInfo } from "../../types/dashboard";
import { formatPeriodLabel } from "../../lib/format";
import { useLang } from "../../contexts/LanguageContext";

interface PeriodSelectorProps {
  periods: PeriodInfo[];
  value: string;
  onChange: (period: string) => void;
}

export function PeriodSelector({ periods, value, onChange }: PeriodSelectorProps) {
  const { t } = useLang();
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
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm transition-colors hover:border-gray-400 dark:border-slate-600 dark:bg-slate-800"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-4 w-4 text-gray-400">
          <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
          <path d="M3.5 9.5h17M8 3v3.5M16 3v3.5" />
        </svg>
        <span className="text-gray-500 dark:text-slate-400">{t("Periode:")}</span>
        <span className="font-semibold text-gray-900 dark:text-white">{t(formatPeriodLabel(value))}</span>
        <svg
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
          className={`h-3.5 w-3.5 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-1 w-60 rounded-md border border-gray-200 bg-white py-1 shadow-lg dark:border-slate-600 dark:bg-slate-800">
          <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-slate-500">
            {t("Periode Data")}
          </p>
          <div className="max-h-72 overflow-y-auto">
            {options.map((opt) => {
              const isActive = value === opt.key;
              const isAll = opt.key === "all";
              return (
                <div key={opt.key}>
                  {isAll && <div className="my-1 h-px bg-gray-100 dark:bg-slate-700" />}
                  <button
                    type="button"
                    onClick={() => { onChange(opt.key); setOpen(false); }}
                    className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors ${
                      isActive
                        ? "bg-red-50 font-semibold text-[#E81E28] dark:bg-red-500/10"
                        : "text-gray-700 hover:bg-gray-50 dark:text-slate-200 dark:hover:bg-slate-700/50"
                    }`}
                  >
                    <span>{t(opt.label)}</span>
                    <span className="text-xs text-gray-400 dark:text-slate-400">{opt.total}</span>
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
