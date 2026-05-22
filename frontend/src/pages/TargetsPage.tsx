import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { TargetsTable } from "../components/dashboard/TargetsTable";
import { CsvUploadPanel } from "../components/dashboard/CsvUploadPanel";
import { getDashboardSnapshot } from "../services/dashboardService";
import type { DashboardSnapshot } from "../types/dashboard";
import type { TargetStatus } from "../types/target";

type FilterValue = TargetStatus | "all";

export function TargetsPage() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<FilterValue>("all");

  useEffect(() => {
    getDashboardSnapshot()
      .then(setSnapshot)
      .finally(() => setIsLoading(false));
    const interval = setInterval(() => {
      getDashboardSnapshot().then(setSnapshot).catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const filteredTargets = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.targets.filter((target) => {
      const queryMatch = !query || 
        target.customerName.toLowerCase().includes(query.toLowerCase()) ||
        target.id.toLowerCase().includes(query.toLowerCase());
      const statusMatch = statusFilter === "all" || target.status === statusFilter;
      return queryMatch && statusMatch;
    });
  }, [query, snapshot, statusFilter]);

  const refreshData = () => {
    getDashboardSnapshot().then(setSnapshot);
  };

  return (
    <AppShell>
      <div className="space-y-10">
        <h1 className="font-serif text-3xl font-medium tracking-wide uppercase text-black">
          Target Management Inventory
        </h1>

        <div className="grid gap-6 lg:grid-cols-[1fr_350px]">
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-black pb-4">
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter by name/ID..."
                  className="w-full sm:w-64 border border-black bg-white px-3 py-2 text-xs font-bold uppercase tracking-wider outline-none"
                />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as FilterValue)}
                  className="w-full sm:w-auto border border-black bg-white px-3 py-2 text-xs font-bold uppercase tracking-wider outline-none"
                >
                  <option value="all">All Records</option>
                  <option value="pending">Pending</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
            </div>
            {isLoading ? (
              <p className="py-10 text-center text-[10px] font-black uppercase tracking-widest text-slate-400">Loading Records...</p>
            ) : (
              <TargetsTable targets={filteredTargets} onRefresh={refreshData} />
            )}
          </div>
          
          <div className="space-y-6">
            <CsvUploadPanel onUploadSuccess={refreshData} />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
