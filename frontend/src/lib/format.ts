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
  if (status === "in_progress") return "In Progress";
  if (status === "completed") return "Completed";
  return "Pending";
}
