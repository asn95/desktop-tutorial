import { useMemo, useState } from "react";
import Papa from "papaparse";
import { apiClient } from "../../lib/apiClient";
import { currentPeriod, formatPeriodLabel } from "../../lib/format";
import { NewPeriodDialog } from "./NewPeriodDialog";
import { useLang } from "../../contexts/LanguageContext";

const REQUIRED_COLUMNS = ["customer_name", "address", "phone", "amount_due"];

type CsvRow = Record<string, string>;

export function CsvUploadPanel({ onUploadSuccess }: { onUploadSuccess?: (period?: string) => void } = {}) {
  const { t } = useLang();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewRows, setPreviewRows] = useState<CsvRow[]>([]);
  const [fullData, setFullData] = useState<CsvRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const period = currentPeriod();
  const periodLabel = formatPeriodLabel(period);

  const previewHeaders = useMemo(() => {
    if (!previewRows.length) return [];
    return Object.keys(previewRows[0]);
  }, [previewRows]);

  const handleFileChange = (file: File | null) => {
    if (!file) return;
    setSelectedFile(file);
    setError(null);
    setMessage(null);
    setPreviewRows([]);
    setFullData([]);

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError(t("Hanya file .csv yang diterima."));
      return;
    }

    Papa.parse<CsvRow>(file, {
      header: true,
      skipEmptyLines: true,
      complete: ({ data, meta }) => {
        const normalizedHeaders = (meta.fields ?? []).map((field) => field.trim().toLowerCase());
        const missingColumns = REQUIRED_COLUMNS.filter((column) => !normalizedHeaders.includes(column));

        if (missingColumns.length > 0) {
          setError(`${t("Kolom wajib tidak ada")}: ${missingColumns.join(", ")}`);
          return;
        }

        setFullData(data);
        setPreviewRows(data.slice(0, 5));
        setMessage(`${t("Siap")}: ${data.length} ${t("baris terbaca.")}`);
      },
      error: (parseError) => {
        setError(parseError.message);
      },
    });
  };

  const handleUpload = async () => {
    if (!fullData.length) return;
    setIsUploading(true);
    setError(null);
    setMessage(null);
    try {
      await apiClient.post(`/targets/upload?period=${encodeURIComponent(period)}`, fullData);
      setMessage(`${t("Berhasil mengunggah")} ${fullData.length} ${t("target ke periode")} ${periodLabel}.`);
      setFullData([]);
      setPreviewRows([]);
      setSelectedFile(null);
      setConfirmOpen(false);
      if (onUploadSuccess) onUploadSuccess(period);
    } catch (err: any) {
      setConfirmOpen(false);
      setError(err.response?.data?.detail || t("Sinkronisasi gagal."));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="rounded-md border border-gray-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t("Sinkronisasi Data")}</h3>
          <p className="mt-1 text-xs text-gray-400 dark:text-slate-400">{t("Impor target penagihan secara massal")}</p>
        </div>
        <span className="rounded border border-gray-200 bg-gray-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300">
          Batch {periodLabel}
        </span>
      </div>

      <div className="mt-6 space-y-4">
        <label className="flex h-32 w-full cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed border-gray-300 bg-gray-50 transition-colors hover:border-gray-400 hover:bg-gray-100 dark:border-slate-600 dark:bg-slate-700/40 dark:hover:border-slate-500">
          <div className="flex flex-col items-center justify-center px-4 text-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="mb-2 h-5 w-5 text-gray-400">
              <path d="M12 16V5M7.5 9.5L12 5l4.5 4.5M4.5 16.5v1.5a2 2 0 002 2h11a2 2 0 002-2v-1.5" />
            </svg>
            <p className="max-w-full truncate text-xs font-semibold text-gray-700 dark:text-slate-200">
              {selectedFile ? selectedFile.name : t("Pilih Sumber CSV")}
            </p>
            <p className="mt-1 text-[10px] text-gray-400 dark:text-slate-500">customer_name, address, phone, amount_due</p>
          </div>
          <input type="file" className="hidden" accept=".csv" onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)} />
        </label>

        <button
          onClick={() => setConfirmOpen(true)}
          disabled={!fullData.length || isUploading}
          className="w-full rounded-md bg-[#E81E28] py-2.5 text-xs font-semibold uppercase tracking-wide text-white transition-colors hover:bg-[#c8161f] disabled:opacity-30"
        >
          {isUploading ? t("Memproses…") : t("Unggah Batch")}
        </button>
      </div>

      {message && <p className="mt-4 text-xs font-medium text-emerald-600">{message}</p>}
      {error && <p className="mt-4 text-xs font-medium text-[#E81E28]">{error}</p>}

      {previewRows.length > 0 && (
        <div className="mt-6 overflow-hidden rounded-md ring-1 ring-black/5 dark:ring-white/10">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-gray-100 bg-gray-50 dark:border-slate-600 dark:bg-slate-700/60">
              <tr>
                {previewHeaders.slice(0, 3).map((h) => (
                  <th key={h} className="px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {previewRows.map((row, i) => (
                <tr key={i}>
                  <td className="px-3 py-2 font-medium text-gray-700 dark:text-slate-200">{row.customer_name}</td>
                  <td className="max-w-[90px] truncate px-3 py-2 text-gray-400 dark:text-slate-400">{row.address}</td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">{row.amount_due}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <NewPeriodDialog
        open={confirmOpen}
        periodLabel={periodLabel}
        rowCount={fullData.length}
        isUploading={isUploading}
        onConfirm={handleUpload}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
