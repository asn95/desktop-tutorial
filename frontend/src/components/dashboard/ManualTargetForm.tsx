import { FormEvent, useState } from "react";
import { apiClient } from "../../lib/apiClient";
import { currentPeriod, formatPeriodLabel } from "../../lib/format";
import { useLang } from "../../contexts/LanguageContext";

const FIELD_CLASS =
  "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none transition focus:border-[#E81E28] focus:ring-2 focus:ring-[#E81E28]/15 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100";

/**
 * Input satu target tanpa CSV.
 *
 * Sengaja memakai POST /targets/upload yang sudah ada dengan array satu elemen,
 * bukan endpoint baru: endpoint itu sudah menulis audit log dan mengantre
 * geocoding alamat, jadi target yang diketik manual otomatis ikut keduanya.
 * Endpoint terpisah berarti dua jalur yang harus dijaga tetap sama selamanya.
 */
export function ManualTargetForm({ onCreated }: { onCreated?: (period?: string) => void } = {}) {
  const { t } = useLang();
  const [customerName, setCustomerName] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [amountDue, setAmountDue] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const period = currentPeriod();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await apiClient.post(`/targets/upload?period=${encodeURIComponent(period)}`, [{
        customer_name: customerName.trim(),
        address: address.trim(),
        phone: phone.trim(),
        amount_due: Number(amountDue),
      }]);
      setMessage(t("Target berhasil ditambahkan."));
      setCustomerName(""); setAddress(""); setPhone(""); setAmountDue("");
      onCreated?.(period);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      // Validasi backend mengembalikan daftar galat per-field (422); ambil pesan
      // pertama saja — menampilkan JSON mentah ke manajer tidak membantu siapa pun.
      setError(
        Array.isArray(detail)
          ? `${detail[0]?.loc?.slice(-1)[0] ?? ""}: ${detail[0]?.msg ?? ""}`.trim()
          : detail ?? t("Gagal menambahkan target."),
      );
    } finally {
      setSaving(false);
    }
  }

  const complete = customerName.trim() && address.trim() && phone.trim() && amountDue !== "";

  return (
    <div className="rounded-md border border-gray-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t("Input Manual")}</h3>
          <p className="mt-1 text-xs text-gray-400 dark:text-slate-400">{t("Tambah satu target tanpa berkas CSV")}</p>
        </div>
        <span className="rounded border border-gray-200 bg-gray-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300">
          Batch {formatPeriodLabel(period)}
        </span>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-3">
        <input
          value={customerName}
          onChange={(e) => setCustomerName(e.target.value)}
          placeholder={t("Nama nasabah")}
          className={FIELD_CLASS}
        />
        <input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder={t("Alamat")}
          className={FIELD_CLASS}
        />
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          inputMode="tel"
          placeholder={t("Nomor telepon")}
          className={FIELD_CLASS}
        />
        <input
          value={amountDue}
          onChange={(e) => setAmountDue(e.target.value)}
          type="number"
          min="0"
          step="1000"
          placeholder={t("Jumlah tagihan")}
          className={FIELD_CLASS}
        />

        <button
          type="submit"
          disabled={!complete || saving}
          className="w-full rounded-md bg-[#E81E28] py-2.5 text-xs font-semibold uppercase tracking-wide text-white transition-colors hover:bg-[#c8161f] disabled:opacity-30"
        >
          {saving ? t("Memproses…") : t("Tambah Target")}
        </button>
      </form>

      {message && <p className="mt-4 text-xs font-medium text-emerald-600">{message}</p>}
      {error && <p className="mt-4 text-xs font-medium text-[#E81E28]">{error}</p>}
    </div>
  );
}
