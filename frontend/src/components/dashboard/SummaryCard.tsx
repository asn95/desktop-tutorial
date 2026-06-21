import type { ReactNode } from "react";

interface SummaryCardProps {
  label: string;
  value: number;
  accent: "default" | "success" | "warning" | "danger";
}

const cfg: Record<SummaryCardProps["accent"], { value: string; chip: string; icon: ReactNode }> = {
  default: {
    value: "text-gray-900",
    chip: "bg-gray-100 text-gray-500",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="h-[18px] w-[18px]">
        <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  success: {
    value: "text-emerald-600",
    chip: "bg-emerald-50 text-emerald-600",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="h-[18px] w-[18px]">
        <circle cx="12" cy="12" r="9" /><path d="M8 12l2.5 2.5L16 9" />
      </svg>
    ),
  },
  warning: {
    value: "text-amber-600",
    chip: "bg-amber-50 text-amber-600",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="h-[18px] w-[18px]">
        <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
      </svg>
    ),
  },
  danger: {
    value: "text-[#E81E28]",
    chip: "bg-red-50 text-[#E81E28]",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="h-[18px] w-[18px]">
        <path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17v.5" />
      </svg>
    ),
  },
};

export function SummaryCard({ label, value, accent }: SummaryCardProps) {
  const c = cfg[accent];
  return (
    <div className="group rounded-2xl border border-gray-100 bg-white p-5 shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)] transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] hover:-translate-y-1 hover:shadow-[0_16px_36px_-14px_rgba(16,24,40,0.22)] sm:p-6">
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
        <span className={`flex h-9 w-9 items-center justify-center rounded-xl ${c.chip}`}>{c.icon}</span>
      </div>
      <div className={`mt-4 text-3xl font-bold tracking-tight sm:text-4xl ${c.value}`}>
        {value.toLocaleString()}
      </div>
    </div>
  );
}
