import { useEffect, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { apiClient } from "../lib/apiClient";
import { formatCurrency } from "../lib/format";

interface OfficerPerf {
  name: string;
  assigned: number;
  completed: number;
  reports: number;
}

interface AnalyticsData {
  distribution: { name: string; value: number }[];
  total_revenue: number;
  revenue: {
    total_due: number;
    collected: number;
    outstanding: number;
    collection_rate: number;
  };
  officer_performance: OfficerPerf[];
  total_targets: number;
  total_reports: number;
  total_comments: number;
  top_issues: { tag: string; count: number }[];
}

const DIST_LABELS: Record<string, string> = {
  "Pending": "Menunggu",
  "In Progress": "Sedang Berjalan",
  "Completed": "Selesai",
};

const TAG_LABELS: Record<string, string> = {
  wrong_address: "Alamat Salah",
  wrong_phone: "Nomor Salah",
  customer_moved: "Customer Pindah",
  not_found: "Tidak Ditemukan",
  other: "Lainnya",
};

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  function fetchData(from?: string, to?: string) {
    setIsLoading(true);
    const params = new URLSearchParams();
    if (from) params.set("date_from", from);
    if (to) params.set("date_to", to);
    apiClient.get<AnalyticsData>(`/analytics/summary?${params}`)
      .then(res => setData(res.data))
      .finally(() => setIsLoading(false));
  }

  useEffect(() => { fetchData(); }, []);

  if (isLoading) {
    return (
      <AppShell>
        <p className="py-20 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          Memproses data analitik...
        </p>
      </AppShell>
    );
  }

  if (!data) return null;

  const revenue = data.revenue ?? { total_due: 0, collected: 0, outstanding: 0, collection_rate: 0 };
  const distribution = data.distribution ?? [];
  const officer_performance = data.officer_performance ?? [];
  const top_issues = data.top_issues ?? [];
  const maxAssigned = Math.max(...officer_performance.map(o => o.assigned), 1);

  return (
    <AppShell>
      <div className="space-y-12 font-sans">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-black dark:text-white">
            Analitik & Kinerja
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white px-2 py-1.5 text-[10px] font-bold"
            />
            <span className="text-[10px] font-bold text-slate-400">s/d</span>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white px-2 py-1.5 text-[10px] font-bold"
            />
            <button
              onClick={() => fetchData(dateFrom, dateTo)}
              className="border border-gray-200 dark:border-slate-600 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide hover:bg-gray-50 transition"
            >
              Filter
            </button>
            {(dateFrom || dateTo) && (
              <button
                onClick={() => { setDateFrom(""); setDateTo(""); fetchData(); }}
                className="text-[10px] font-bold text-red-600 hover:underline"
              >
                Bersihkan
              </button>
            )}
          </div>
        </div>

        {/* Revenue Section */}
        <section>
          <div className="border-b-2 border-gray-200 pb-2 mb-8">
            <h2 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-500">Ringkasan Pendapatan</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-0 overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
            <div className="p-5 sm:p-8 border-b sm:border-b-0 sm:border-r border-gray-200">
              <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-400 mb-3">Total Tunggakan</p>
              <p className="text-2xl sm:text-4xl font-medium tracking-tighter text-[#1a1c1e]">{formatCurrency(revenue.total_due)}</p>
            </div>
            <div className="p-5 sm:p-8 border-b sm:border-b-0 sm:border-r border-gray-200">
              <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-400 mb-3">Terkumpul</p>
              <p className="text-2xl sm:text-4xl font-medium tracking-tighter text-[#1a1c1e]">{formatCurrency(revenue.collected)}</p>
            </div>
            <div className="p-5 sm:p-8">
              <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-400 mb-3">Tunggakan</p>
              <p className="text-2xl sm:text-4xl font-medium tracking-tighter text-red-600">{formatCurrency(revenue.outstanding)}</p>
            </div>
          </div>

          {/* Collection progress */}
          <div className="mt-6 rounded-2xl border border-gray-100 p-6 bg-white">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Progres Penagihan</span>
              <span className="text-sm font-semibold text-[#1a1c1e]">{revenue.collection_rate}%</span>
            </div>
            <div className="w-full h-2 bg-slate-100">
              <div className="h-full bg-[#E81E28] transition-all" style={{ width: `${revenue.collection_rate}%` }} />
            </div>
          </div>
        </section>

        {/* Status Breakdown */}
        <section>
          <div className="border-b-2 border-gray-200 pb-2 mb-8">
            <h2 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-500">Rincian Status Target</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-0 overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
            {distribution.map((d, i) => {
              const pct = data.total_targets > 0 ? Math.round((d.value / data.total_targets) * 100) : 0;
              const colors = ["border-red-500", "border-amber-500", "border-green-500"];
              const textColors = ["text-red-600", "text-amber-600", "text-green-600"];
              return (
                <div key={d.name} className={`p-5 sm:p-8 ${i < 2 ? "border-b sm:border-b-0 sm:border-r border-gray-200" : ""}`}>
                  <div className={`border-l-4 ${colors[i]} pl-4`}>
                    <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-400">{DIST_LABELS[d.name] ?? d.name}</p>
                    <div className="flex items-baseline gap-2 mt-2">
                      <span className="text-4xl sm:text-5xl font-medium tracking-tighter text-[#1a1c1e]">{d.value}</span>
                      <span className={`text-sm font-semibold ${textColors[i]}`}>{pct}%</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Officer Performance */}
        <section>
          <div className="border-b-2 border-gray-200 pb-2 mb-8">
            <h2 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-500">Kinerja Petugas</h2>
          </div>

          {officer_performance.length === 0 ? (
            <p className="py-10 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400 rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
              No officer assignments yet.
            </p>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
              {[...officer_performance]
                .sort((a, b) => b.assigned - a.assigned)
                .map((o, i) => {
                  const rate = o.assigned > 0 ? Math.round((o.completed / o.assigned) * 100) : 0;
                  const barW = Math.round((o.assigned / maxAssigned) * 100);
                  return (
                    <div key={o.name} className={`flex items-center gap-3 sm:gap-6 px-4 sm:px-6 py-4 sm:py-5 ${i > 0 ? "border-t border-slate-200" : ""}`}>
                      <span className="text-slate-300 text-sm font-semibold w-5 sm:w-6 text-right shrink-0">{i + 1}</span>
                      <div className="w-28 sm:w-40 shrink-0">
                        <p className="text-xs font-bold text-[#1a1c1e]">{o.name}</p>
                        <p className="text-[9px] text-slate-400 mt-0.5">
                          {o.reports} laporan dikirim
                        </p>
                      </div>
                      <div className="flex-1 hidden sm:block">
                        <div className="w-full h-5 bg-slate-50 relative">
                          <div className="absolute inset-y-0 left-0 bg-slate-200" style={{ width: `${barW}%` }} />
                          <div className="absolute inset-y-0 left-0 bg-[#E81E28]" style={{ width: `${Math.round((o.completed / maxAssigned) * 100)}%` }} />
                        </div>
                      </div>
                      <div className="text-right shrink-0 w-20 sm:w-28">
                        <span className="text-xs font-semibold text-[#1a1c1e]">{o.completed}</span>
                        <span className="text-xs text-slate-400"> / {o.assigned}</span>
                        <span className={`ml-1 sm:ml-2 text-[10px] font-semibold ${rate >= 50 ? "text-green-600" : rate > 0 ? "text-amber-600" : "text-slate-400"}`}>
                          {rate}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              <div className="border-t border-slate-200 px-6 py-3 flex items-center gap-4 text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                <span className="flex items-center gap-1.5"><span className="w-3 h-2 bg-[#E81E28] inline-block" /> Selesai</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-2 bg-slate-200 inline-block" /> Ditugaskan</span>
              </div>
            </div>
          )}
        </section>

        {/* Bottom: Activity + Issues side by side */}
        <section className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-8">
          {/* Activity Summary */}
          <div>
            <div className="border-b-2 border-gray-200 pb-2 mb-8">
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-500">Ringkasan Aktivitas</h2>
            </div>
            <div className="border border-gray-200 bg-white divide-y divide-slate-100">
              <ActivityRow label="Target Terdaftar" value={data.total_targets} />
              <ActivityRow label="Laporan Lapangan Dikirim" value={data.total_reports} />
              <ActivityRow label="Komentar Petugas" value={data.total_comments} />
              <ActivityRow label="Petugas Aktif" value={officer_performance.length} />
              <ActivityRow label="Rata-rata Target per Petugas" value={
                officer_performance.length > 0
                  ? Math.round(data.total_targets / officer_performance.length)
                  : 0
              } />
            </div>
          </div>

          {/* Field Issues */}
          <div>
            <div className="border-b-2 border-gray-200 pb-2 mb-8">
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-500">Kendala Lapangan Dilaporkan</h2>
            </div>
            <div className="border border-gray-200 bg-white">
              {top_issues.length === 0 ? (
                <p className="px-6 py-10 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">
                  Belum ada kendala dilaporkan.
                </p>
              ) : (
                top_issues.map((issue, i) => {
                  const maxCount = Math.max(...top_issues.map(x => x.count));
                  const barW = Math.round((issue.count / maxCount) * 100);
                  return (
                    <div key={issue.tag} className={`flex items-center justify-between px-6 py-4 ${i > 0 ? "border-t border-slate-100" : ""}`}>
                      <span className="text-xs font-bold text-[#1a1c1e]">{TAG_LABELS[issue.tag] ?? issue.tag}</span>
                      <div className="flex items-center gap-3">
                        <div className="w-24 h-1.5 bg-slate-100">
                          <div className="h-full bg-red-500" style={{ width: `${barW}%` }} />
                        </div>
                        <span className="text-xs font-semibold text-[#1a1c1e] w-6 text-right">{issue.count}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function ActivityRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between px-6 py-4">
      <span className="text-xs font-bold text-slate-600">{label}</span>
      <span className="text-lg font-medium tracking-tight text-[#1a1c1e]">{value}</span>
    </div>
  );
}
