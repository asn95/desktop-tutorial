import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { TargetsTable } from "../components/dashboard/TargetsTable";
import { CsvUploadPanel } from "../components/dashboard/CsvUploadPanel";
import { getDashboardSnapshot } from "../services/dashboardService";
import { getUsers } from "../services/userService";
import { apiClient } from "../lib/apiClient";
import type { DashboardSnapshot } from "../types/dashboard";
import type { TargetStatus } from "../types/target";
import type { User } from "../types/user";

type FilterValue = TargetStatus | "all";

export function TargetsPage() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<FilterValue>("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [officers, setOfficers] = useState<User[]>([]);
  const [bulkOfficer, setBulkOfficer] = useState("");
  const [bulkAssigning, setBulkAssigning] = useState(false);

  useEffect(() => {
    Promise.all([getDashboardSnapshot(), getUsers()])
      .then(([snap, users]) => {
        setSnapshot(snap);
        setOfficers(users.filter(u => u.role === "officer"));
      })
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

  const pendingTargets = useMemo(() => filteredTargets.filter(t => t.status === "pending"), [filteredTargets]);

  const refreshData = () => {
    getDashboardSnapshot().then(setSnapshot);
    setSelected(new Set());
  };

  function toggleSelect(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === pendingTargets.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(pendingTargets.map(t => t.id)));
    }
  }

  async function handleBulkAssign() {
    if (!bulkOfficer || selected.size === 0) return;
    setBulkAssigning(true);
    try {
      await apiClient.post("/targets/bulk-assign", {
        target_ids: Array.from(selected),
        officer_id: bulkOfficer,
      });
      refreshData();
      setBulkOfficer("");
    } catch {
      alert("Gagal menugaskan massal.");
    } finally {
      setBulkAssigning(false);
    }
  }

  async function handleExport() {
    try {
      const res = await apiClient.get("/targets/export/csv", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "c3mr_targets_export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Gagal mengekspor.");
    }
  }

  return (
    <AppShell>
      <div className="space-y-10">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-black dark:text-white">
            Inventaris Manajemen Target
          </h1>
          <button
            onClick={handleExport}
            className="border border-gray-200 dark:border-slate-600 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide hover:bg-gray-50 transition w-fit"
          >
            Ekspor CSV
          </button>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_350px]">
          <div className="space-y-6 min-w-0">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-gray-200 dark:border-slate-600 pb-4">
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Cari nama/ID..."
                  className="w-full sm:w-64 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white px-3 py-2 text-xs font-bold uppercase tracking-wider outline-none"
                />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as FilterValue)}
                  className="w-full sm:w-auto border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white px-3 py-2 text-xs font-bold uppercase tracking-wider outline-none"
                >
                  <option value="all">Semua</option>
                  <option value="pending">Menunggu</option>
                  <option value="in_progress">Sedang Berjalan</option>
                  <option value="completed">Selesai</option>
                </select>
              </div>
            </div>

            {/* Bulk Assign Bar */}
            {selected.size > 0 && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 rounded-xl border border-[#E81E28]/40 bg-red-50 dark:bg-red-900/20 px-4 py-3">
                <span className="text-xs font-bold text-[#E81E28] dark:text-red-300">
                  {selected.size} dipilih
                </span>
                <select
                  value={bulkOfficer}
                  onChange={e => setBulkOfficer(e.target.value)}
                  className="border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white px-2 py-1 text-[10px] font-bold"
                >
                  <option value="">Pilih Petugas</option>
                  {officers.map(o => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </select>
                <button
                  onClick={handleBulkAssign}
                  disabled={!bulkOfficer || bulkAssigning}
                  className="bg-[#E81E28] text-white px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-30"
                >
                  {bulkAssigning ? "Menugaskan..." : "Tugaskan Semua"}
                </button>
                <button
                  onClick={() => setSelected(new Set())}
                  className="text-[10px] font-bold text-slate-500 hover:underline"
                >
                  Bersihkan
                </button>
              </div>
            )}

            {isLoading ? (
              <p className="py-10 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400">Memuat data...</p>
            ) : (
              <TargetsTable
                targets={filteredTargets}
                onRefresh={refreshData}
                selected={selected}
                onToggleSelect={toggleSelect}
                onToggleAll={toggleAll}
                pendingCount={pendingTargets.length}
              />
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
