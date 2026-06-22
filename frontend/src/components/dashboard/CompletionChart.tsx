import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { DashboardStats } from "../../types/dashboard";

const COLORS = ["#16a34a", "#d97706", "#dc2626"];

export function CompletionChart({ stats }: { stats: DashboardStats }) {
  const chartData = [
    { name: "Completed", value: stats.completed },
    { name: "In Progress", value: stats.inProgress },
    { name: "Pending", value: stats.pending },
  ];

  return (
    <div className="rounded-xl border border-c3mr-border bg-c3mr-surface p-4">
      <p className="mb-4 text-sm font-medium text-c3mr-text">Tingkat Penyelesaian</p>
      <div className="h-56 w-full">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={chartData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label>
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-sm text-c3mr-muted">
        {stats.completed} of {stats.totalTargets} targets completed
      </p>
    </div>
  );
}
