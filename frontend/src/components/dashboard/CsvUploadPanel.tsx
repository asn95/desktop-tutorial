import { useMemo, useState } from "react";
import Papa from "papaparse";
import { apiClient } from "../../lib/apiClient";

const REQUIRED_COLUMNS = ["customer_name", "address", "phone", "amount_due"];

type CsvRow = Record<string, string>;

export function CsvUploadPanel({ onUploadSuccess }: { onUploadSuccess?: () => void } = {}) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewRows, setPreviewRows] = useState<CsvRow[]>([]);
  const [fullData, setFullData] = useState<CsvRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

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
      setError("Hanya file .csv yang diterima.");
      return;
    }

    Papa.parse<CsvRow>(file, {
      header: true,
      skipEmptyLines: true,
      complete: ({ data, meta }) => {
        const normalizedHeaders = (meta.fields ?? []).map((field) => field.trim().toLowerCase());
        const missingColumns = REQUIRED_COLUMNS.filter((column) => !normalizedHeaders.includes(column));

        if (missingColumns.length > 0) {
          setError(`Kolom wajib tidak ada: ${missingColumns.join(", ")}`);
          return;
        }

        setFullData(data);
        setPreviewRows(data.slice(0, 5));
        setMessage(`Siap: ${data.length} baris terbaca.`);
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
      await apiClient.post("/targets/upload", fullData);
      setMessage(`Berhasil menyinkronkan ${fullData.length} baris.`);
      setFullData([]);
      setPreviewRows([]);
      setSelectedFile(null);
      if (onUploadSuccess) onUploadSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Sinkronisasi gagal.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="border border-gray-200 bg-white p-6 shadow-sm">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-black">Sinkronisasi Data</h3>
      <p className="mt-1 text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
        Impor target penagihan secara massal
      </p>

      <div className="mt-6 space-y-4">
        <label className="flex h-32 w-full cursor-pointer flex-col items-center justify-center border-2 border-dashed border-slate-200 bg-slate-50 transition hover:bg-slate-100">
          <div className="flex flex-col items-center justify-center pt-5 pb-6">
            <p className="mb-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
              {selectedFile ? selectedFile.name : "Pilih Sumber CSV"}
            </p>
            <p className="text-[10px] font-medium text-slate-400">customer_name, address, phone, amount_due</p>
          </div>
          <input type="file" className="hidden" accept=".csv" onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)} />
        </label>

        <button
          onClick={handleUpload}
          disabled={!fullData.length || isUploading}
          className="w-full rounded-lg bg-[#E81E28] py-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-white transition hover:bg-[#c8161f] disabled:opacity-30"
        >
          {isUploading ? "Memproses..." : "Unggah Batch"}
        </button>
      </div>

      {message && <p className="mt-4 text-[10px] font-bold uppercase text-green-600 tracking-wider">{message}</p>}
      {error && <p className="mt-4 text-[10px] font-bold uppercase text-red-600 tracking-wider">{error}</p>}

      {previewRows.length > 0 && (
        <div className="mt-6 overflow-hidden border border-gray-200">
          <table className="w-full text-left text-[9px] font-bold uppercase tracking-tighter">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>{previewHeaders.slice(0, 3).map(h => <th key={h} className="px-2 py-2">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {previewRows.map((row, i) => (
                <tr key={i}>
                  <td className="px-2 py-2 text-slate-600">{row.customer_name}</td>
                  <td className="px-2 py-2 text-slate-400 truncate max-w-[80px]">{row.address}</td>
                  <td className="px-2 py-2 text-slate-600">{row.amount_due}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
