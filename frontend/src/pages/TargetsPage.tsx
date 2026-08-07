import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { TargetsTable } from "../components/dashboard/TargetsTable";
import { CsvUploadPanel } from "../components/dashboard/CsvUploadPanel";
import { ManualTargetForm } from "../components/dashboard/ManualTargetForm";
import { PeriodSelector } from "../components/dashboard/PeriodSelector";

// Dashboard cukup 50 baris terbaru, tapi di halaman ini manajer memilih dan
// menugaskan secara massal — kalau daftarnya terpotong, target yang tidak
// tampil mustahil dipilih. Dibatasi di sisi server pada 2000.
const ALL_ROWS = 2000;
import { getDashboardSnapshot, getPeriods } from "../services/dashboardService";
import { getUsers } from "../services/userService";
import { apiClient } from "../lib/apiClient";
import { useLang } from "../contexts/LanguageContext";
import type { DashboardSnapshot, PeriodInfo } from "../types/dashboard";
import type { TargetStatus } from "../types/target";
import type { User } from "../types/user";

type FilterValue = TargetStatus | "all";

export function TargetsPage() {
  const { t } = useLang();
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<FilterValue>("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [officers, setOfficers] = useState<User[]>([]);
  const [bulkOfficer, setBulkOfficer] = useState("");
  const [bulkAssigning, setBulkAssigning] = useState(false);
  const [periods, setPeriods] = useState<PeriodInfo[]>([]);
  const [period, setPeriod] = useState<string | null>(null);

  useEffect(() => {
    getPeriods()
      .then((res) => {
        setPeriods(res.periods);
        setPeriod(res.active ?? "all");
      })
      .catch(() => setPeriod("all"));
  }, []);

  useEffect(() => {
    if (!period) return;
    Promise.all([getDashboardSnapshot(period, ALL_ROWS), getUsers()])
      .then(([snap, users]) => {
        setSnapshot(snap);
        setOfficers(users.filter(u => u.role === "officer"));
      })
      .finally(() => setIsLoading(false));
    const interval = setInterval(() => {
      getDashboardSnapshot(period, ALL_ROWS).then(setSnapshot).catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, [period]);

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
    getDashboardSnapshot(period, ALL_ROWS).then(setSnapshot);
    setSelected(new Set());
  };

  // After a CSV upload, re-resolve periods and jump to the batch that was just uploaded.
  const handleUploadSuccess = (uploadedPeriod?: string) => {
    getPeriods()
      .then((res) => {
        setPeriods(res.periods);
        const next = uploadedPeriod ?? res.active ?? "all";
        if (next !== period) setPeriod(next);
        else refreshData();
      })
      .catch(() => refreshData());
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
      alert(t("Gagal menugaskan massal."));
    } finally {
      setBulkAssigning(false);
    }
  }

  async function handleExport() {
    try {
      const exportQuery = period && period !== "all" ? `?period=${encodeURIComponent(period)}` : "";
      const res = await apiClient.get(`/targets/export/csv${exportQuery}`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "c3mr_targets_export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert(t("Gagal mengekspor."));
    }
  }

  return (
    <AppShell>
      <div className="space-y-10">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-black dark:text-white">
            {t("Inventaris Manajemen Target")}
          </h1>
          <div className="flex flex-wrap items-center gap-3">
            {period && <PeriodSelector periods={periods} value={period} onChange={setPeriod} />}
            <button
              onClick={handleExport}
              className="border border-gray-200 dark:border-slate-600 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide hover:bg-gray-50 transition w-fit"
            >
              {t("Ekspor CSV")}
            </button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_350px]">
          <div className="space-y-6 min-w-0">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-gray-200 dark:border-slate-600 pb-4">
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t("Cari nama/ID...")}
                  className="w-full sm:w-64 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white px-3 py-2 text-xs font-bold uppercase tracking-wider outline-none"
                />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as FilterValue)}
                  className="w-full sm:w-auto border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white px-3 py-2 text-xs font-bold uppercase tracking-wider outline-none"
                >
                  <option value="all">{t("Semua")}</option>
                  <option value="pending">{t("Menunggu")}</option>
                  <option value="in_progress">{t("Sedang Berjalan")}</option>
                  <option value="completed">{t("Selesai")}</option>
                </select>
              </div>
            </div>

            {/* Bulk Assign Bar */}
            {selected.size > 0 && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 rounded-md border border-[#E81E28]/40 bg-red-50 dark:bg-red-900/20 px-4 py-3">
                <span className="text-xs font-bold text-[#E81E28] dark:text-red-300">
                  {selected.size} {t("dipilih")}
                </span>
                <select
                  value={bulkOfficer}
                  onChange={e => setBulkOfficer(e.target.value)}
                  className="border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white px-2 py-1 text-[10px] font-bold"
                >
                  <option value="">{t("Pilih Petugas")}</option>
                  {officers.map(o => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </select>
                <button
                  onClick={handleBulkAssign}
                  disabled={!bulkOfficer || bulkAssigning}
                  className="bg-[#E81E28] text-white px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-30"
                >
                  {bulkAssigning ? t("Menugaskan...") : t("Tugaskan Semua")}
                </button>
                <button
                  onClick={() => setSelected(new Set())}
                  className="text-[10px] font-bold text-slate-500 hover:underline"
                >
                  {t("Bersihkan")}
                </button>
              </div>
            )}

            {!isLoading && (
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                {t("Menampilkan")} {filteredTargets.length} {t("dari")} {snapshot?.stats.totalTargets ?? 0} {t("target")}
                {filteredTargets.length < (snapshot?.stats.totalTargets ?? 0) && ` · ${t("disaring")}`}
              </p>
            )}

            {isLoading ? (
              <p className="py-10 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400">{t("Memuat data...")}</p>
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
            <CsvUploadPanel onUploadSuccess={handleUploadSuccess} />
            <ManualTargetForm onCreated={handleUploadSuccess} />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
