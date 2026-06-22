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
