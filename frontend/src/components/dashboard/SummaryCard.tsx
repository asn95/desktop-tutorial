interface SummaryCardProps {
  label: string;
  value: number;
  accent: "default" | "success" | "warning" | "danger";
}

export function SummaryCard({ label, value }: SummaryCardProps) {
  return (
    <div className="border-b border-r border-black p-8">
      <p className="mb-4 text-[10px] font-black uppercase tracking-[0.2em] text-[#1a1c1e] opacity-60">
        {label}
      </p>
      <div className="text-5xl font-medium tracking-tighter text-[#1a1c1e]">
        {value.toLocaleString()}
      </div>
    </div>
  );
}
