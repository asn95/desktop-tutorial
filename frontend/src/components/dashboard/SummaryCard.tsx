interface SummaryCardProps {
  label: string;
  value: number;
  accent: "default" | "success" | "warning" | "danger";
}

const ACCENT_BAR: Record<SummaryCardProps["accent"], string> = {
  default: "bg-gray-400",
  success: "bg-emerald-600",
  warning: "bg-amber-500",
  danger: "bg-[#E81E28]",
};

const ACCENT_VALUE: Record<SummaryCardProps["accent"], string> = {
  default: "text-gray-900",
  success: "text-emerald-700",
  warning: "text-amber-600",
  danger: "text-[#E81E28]",
};

export function SummaryCard({ label, value, accent }: SummaryCardProps) {
  return (
    <div className="relative overflow-hidden rounded-md border border-gray-200 bg-white py-4 pl-5 pr-4 sm:py-5">
      <span className={`absolute inset-y-0 left-0 w-[3px] ${ACCENT_BAR[accent]}`} />
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <div className={`mt-2 text-3xl font-bold tracking-tight ${ACCENT_VALUE[accent]}`}>
        {value.toLocaleString()}
      </div>
    </div>
  );
}
