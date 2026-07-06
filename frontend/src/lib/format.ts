import type { TargetStatus } from "../types/target";

const currencyFormatter = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
});

export function formatCurrency(value: number) {
  return currencyFormatter.format(value);
}

export function formatStatus(status: TargetStatus) {
  if (status === "in_progress") return "Sedang Berjalan";
  if (status === "completed") return "Selesai";
  return "Menunggu";
}

const MONTHS_ID = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember",
];

/** "2026-07" → "Juli 2026"; "all" → "Semua Periode"; anything else returned as-is. */
export function formatPeriodLabel(period?: string | null) {
  if (!period || period === "all") return "Semua Periode";
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  if (!match) return period;
  const monthIndex = Number(match[2]) - 1;
  if (monthIndex < 0 || monthIndex > 11) return period;
  return `${MONTHS_ID[monthIndex]} ${match[1]}`;
}

/** Current month in the "YYYY-MM" period format used by the backend. */
export function currentPeriod() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}
