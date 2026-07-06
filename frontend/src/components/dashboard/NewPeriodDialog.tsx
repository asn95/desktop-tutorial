import { useEffect, useState } from "react";

const EASE = "ease-[cubic-bezier(0.32,0.72,0,1)]";

interface NewPeriodDialogProps {
  open: boolean;
  periodLabel: string;
  rowCount: number;
  isUploading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function NewPeriodDialog({ open, periodLabel, rowCount, isUploading, onConfirm, onCancel }: NewPeriodDialogProps) {
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (open) {
      const raf = requestAnimationFrame(() => setShown(true));
      return () => cancelAnimationFrame(raf);
    }
    setShown(false);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !isUploading) onCancel();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, isUploading, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      {/* Frosted overlay */}
      <div
        onClick={() => !isUploading && onCancel()}
        className={`absolute inset-0 bg-gray-950/40 backdrop-blur-sm transition-opacity duration-500 ${shown ? "opacity-100" : "opacity-0"}`}
      />

      {/* Double-bezel card */}
      <div
        className={`relative w-full max-w-md transition-all duration-700 ${EASE} ${
          shown ? "translate-y-0 scale-100 opacity-100" : "translate-y-8 scale-95 opacity-0"
        }`}
      >
        <div className="rounded-[1.75rem] bg-white/60 p-1.5 ring-1 ring-black/5 shadow-[0_24px_80px_-24px_rgba(16,24,40,0.4)] dark:bg-slate-900/60 dark:ring-white/10">
          <div className="rounded-[calc(1.75rem-0.375rem)] bg-white px-6 py-7 shadow-[inset_0_1px_1px_rgba(255,255,255,0.7)] sm:px-8 dark:bg-slate-800">
            <span className="inline-flex w-fit items-center rounded-full bg-red-50 px-3 py-1 text-[10px] font-medium uppercase tracking-[0.2em] text-[#E81E28] dark:bg-red-500/10">
              Batch Baru
            </span>

            <div className="mt-5 flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-[#E81E28] dark:bg-red-500/10">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" className="h-5 w-5">
                <rect x="3" y="5" width="18" height="16" rx="3.5" />
                <path d="M3 10h18M8 2.5V6M16 2.5V6M12 13v5M9.5 15.5h5" />
              </svg>
            </div>

            <h2 className="mt-4 text-xl font-bold tracking-tight text-gray-900 dark:text-white">
              Mulai periode {periodLabel}?
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-gray-500 dark:text-slate-400">
              <span className="font-semibold text-gray-700 dark:text-slate-200">{rowCount} target</span> akan diunggah
              sebagai batch <span className="font-semibold text-gray-700 dark:text-slate-200">{periodLabel}</span>.
              Data periode sebelumnya tetap tersimpan dan bisa dibuka kapan saja lewat pemilih periode di dasbor.
            </p>

            <div className="mt-7 flex flex-col-reverse gap-2.5 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={onCancel}
                disabled={isUploading}
                className={`rounded-full px-5 py-2.5 text-sm font-medium text-gray-600 ring-1 ring-black/10 transition-all duration-500 ${EASE} hover:bg-gray-50 active:scale-[0.98] disabled:opacity-40 dark:text-slate-300 dark:ring-white/15 dark:hover:bg-slate-700/50`}
              >
                Batal
              </button>
              <button
                type="button"
                onClick={onConfirm}
                disabled={isUploading}
                className={`group flex items-center justify-center gap-3 rounded-full bg-[#E81E28] py-1.5 pl-5 pr-1.5 text-sm font-semibold text-white transition-all duration-500 ${EASE} hover:bg-[#c8161f] active:scale-[0.98] disabled:opacity-40`}
              >
                {isUploading ? "Mengunggah…" : "Ya, Unggah Sekarang"}
                <span className={`flex h-8 w-8 items-center justify-center rounded-full bg-white/15 transition-transform duration-500 ${EASE} group-hover:-translate-y-px group-hover:translate-x-0.5 group-hover:scale-105`}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5">
                    <path d="M7 17L17 7M9 7h8v8" />
                  </svg>
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
