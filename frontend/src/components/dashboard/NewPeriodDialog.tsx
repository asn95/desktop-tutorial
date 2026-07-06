import { useEffect } from "react";

interface NewPeriodDialogProps {
  open: boolean;
  periodLabel: string;
  rowCount: number;
  isUploading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function NewPeriodDialog({ open, periodLabel, rowCount, isUploading, onConfirm, onCancel }: NewPeriodDialogProps) {
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
      <div
        onClick={() => !isUploading && onCancel()}
        className="absolute inset-0 bg-gray-900/50"
      />

      <div className="relative w-full max-w-md rounded-md border border-gray-200 bg-white p-6 shadow-xl dark:border-slate-600 dark:bg-slate-800">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white">
          Mulai periode {periodLabel}?
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-gray-600 dark:text-slate-300">
          <span className="font-semibold">{rowCount} target</span> akan diunggah
          sebagai batch <span className="font-semibold">{periodLabel}</span>.
          Data periode sebelumnya tetap tersimpan dan bisa dibuka kapan saja lewat pemilih periode.
        </p>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isUploading}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-40 dark:border-slate-500 dark:text-slate-200 dark:hover:bg-slate-700/50"
          >
            Batal
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isUploading}
            className="rounded-md bg-[#E81E28] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#c8161f] disabled:opacity-40"
          >
            {isUploading ? "Mengunggah…" : "Ya, Unggah Sekarang"}
          </button>
        </div>
      </div>
    </div>
  );
}
