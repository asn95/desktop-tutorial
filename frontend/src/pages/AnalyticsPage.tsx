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

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    apiClient.get<AnalyticsData>("/analytics/summary")
      .then(res => setData(res.data))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <AppShell>
        <p className="py-20 text-center text-[10px] font-black uppercase tracking-widest text-slate-400">
          Processing Analytics Data...
        </p>
      </AppShell>
    );
  }

  if (!data) return null;

  const { revenue, distribution, officer_performance, top_issues } = data;
  const maxAssigned = Math.max(...officer_performance.map(o => o.assigned), 1);

  return (
    <AppShell>
      <div className="space-y-12 font-sans">
        <h1 className="font-serif text-3xl font-medium tracking-wide uppercase text-black">
          Analytics & Performance
        </h1>

        {/* Revenue Section */}
        <section>
          <div className="border-b-2 border-black pb-2 mb-8">
            <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500">Revenue Overview</h2>
          </div>

          <div className="grid lg:grid-cols-[1fr_1fr_1fr] gap-0 border border-black">
            <div className="p-8 border-r border-black">
              <p className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400 mb-3">Total Outstanding</p>
              <p className="text-4xl font-medium tracking-tighter text-[#1a1c1e]">{formatCurrency(revenue.total_due)}</p>
            </div>
            <div className="p-8 border-r border-black">
              <p className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400 mb-3">Collected</p>
              <p className="text-4xl font-medium tracking-tighter text-[#1a1c1e]">{formatCurrency(revenue.collected)}</p>
            </div>
            <div className="p-8">
              <p className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400 mb-3">Outstanding</p>
              <p className="text-4xl font-medium tracking-tighter text-red-600">{formatCurrency(revenue.outstanding)}</p>
            </div>
          </div>

          {/* Collection progress */}
          <div className="mt-6 border border-black p-6 bg-white">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Collection Progress</span>
              <span className="text-sm font-black text-[#1a1c1e]">{revenue.collection_rate}%</span>
            </div>
            <div className="w-full h-2 bg-slate-100">
              <div className="h-full bg-[#1a1c1e] transition-all" style={{ width: `${revenue.collection_rate}%` }} />
            </div>
          </div>
        </section>

        {/* Status Breakdown */}
        <section>
          <div className="border-b-2 border-black pb-2 mb-8">
            <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500">Target Status Breakdown</h2>
          </div>

          <div className="grid lg:grid-cols-3 gap-0 border border-black">
            {distribution.map((d, i) => {
              const pct = data.total_targets > 0 ? Math.round((d.value / data.total_targets) * 100) : 0;
              const colors = ["border-red-500", "border-amber-500", "border-green-500"];
              const textColors = ["text-red-600", "text-amber-600", "text-green-600"];
              return (
                <div key={d.name} className={`p-8 ${i < 2 ? "border-r border-black" : ""}`}>
                  <div className={`border-l-4 ${colors[i]} pl-4`}>
                    <p className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">{d.name}</p>
                    <div className="flex items-baseline gap-2 mt-2">
                      <span className="text-5xl font-medium tracking-tighter text-[#1a1c1e]">{d.value}</span>
                      <span className={`text-sm font-black ${textColors[i]}`}>{pct}%</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Officer Performance */}
        <section>
          <div className="border-b-2 border-black pb-2 mb-8">
            <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500">Officer Performance</h2>
          </div>

          {officer_performance.length === 0 ? (
            <p className="py-10 text-center text-[10px] font-bold uppercase tracking-widest text-slate-400 border border-black bg-white">
              No officer assignments yet.
            </p>
          ) : (
            <div className="border border-black bg-white">
              {[...officer_performance]
                .sort((a, b) => b.assigned - a.assigned)
                .map((o, i) => {
                  const rate = o.assigned > 0 ? Math.round((o.completed / o.assigned) * 100) : 0;
                  const barW = Math.round((o.assigned / maxAssigned) * 100);
                  return (
                    <div key={o.name} className={`flex items-center gap-6 px-6 py-5 ${i > 0 ? "border-t border-slate-200" : ""}`}>
                      <span className="text-slate-300 text-sm font-black w-6 text-right shrink-0">{i + 1}</span>
                      <div className="w-40 shrink-0">
                        <p className="text-xs font-bold text-[#1a1c1e]">{o.name}</p>
                        <p className="text-[9px] text-slate-400 mt-0.5">
                          {o.reports} report{o.reports !== 1 ? "s" : ""} filed
                        </p>
                      </div>
                      <div className="flex-1">
                        <div className="w-full h-5 bg-slate-50 relative">
                          <div className="absolute inset-y-0 left-0 bg-slate-200" style={{ width: `${barW}%` }} />
                          <div className="absolute inset-y-0 left-0 bg-[#1a1c1e]" style={{ width: `${Math.round((o.completed / maxAssigned) * 100)}%` }} />
                        </div>
                      </div>
                      <div className="text-right shrink-0 w-28">
                        <span className="text-xs font-black text-[#1a1c1e]">{o.completed}</span>
                        <span className="text-xs text-slate-400"> / {o.assigned}</span>
                        <span className={`ml-2 text-[10px] font-black ${rate >= 50 ? "text-green-600" : rate > 0 ? "text-amber-600" : "text-slate-400"}`}>
                          {rate}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              <div className="border-t border-slate-200 px-6 py-3 flex items-center gap-4 text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                <span className="flex items-center gap-1.5"><span className="w-3 h-2 bg-[#1a1c1e] inline-block" /> Completed</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-2 bg-slate-200 inline-block" /> Assigned</span>
              </div>
            </div>
          )}
        </section>

        {/* Bottom: Activity + Issues side by side */}
        <section className="grid lg:grid-cols-[1fr_1fr] gap-10">
          {/* Activity Summary */}
          <div>
            <div className="border-b-2 border-black pb-2 mb-8">
              <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500">Activity Summary</h2>
            </div>
            <div className="border border-black bg-white divide-y divide-slate-100">
              <ActivityRow label="Targets Registered" value={data.total_targets} />
              <ActivityRow label="Field Reports Submitted" value={data.total_reports} />
              <ActivityRow label="Officer Comments" value={data.total_comments} />
              <ActivityRow label="Active Officers" value={officer_performance.length} />
              <ActivityRow label="Avg. Targets per Officer" value={
                officer_performance.length > 0
                  ? Math.round(data.total_targets / officer_performance.length)
                  : 0
              } />
            </div>
          </div>

          {/* Field Issues */}
          <div>
            <div className="border-b-2 border-black pb-2 mb-8">
              <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500">Reported Field Issues</h2>
            </div>
            <div className="border border-black bg-white">
              {top_issues.length === 0 ? (
                <p className="px-6 py-10 text-center text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  No issues reported yet.
                </p>
              ) : (
                top_issues.map((issue, i) => {
                  const maxCount = Math.max(...top_issues.map(x => x.count));
                  const barW = Math.round((issue.count / maxCount) * 100);
                  return (
                    <div key={issue.tag} className={`flex items-center justify-between px-6 py-4 ${i > 0 ? "border-t border-slate-100" : ""}`}>
                      <span className="text-xs font-bold text-[#1a1c1e]">{issue.tag}</span>
                      <div className="flex items-center gap-3">
                        <div className="w-24 h-1.5 bg-slate-100">
                          <div className="h-full bg-red-500" style={{ width: `${barW}%` }} />
                        </div>
                        <span className="text-xs font-black text-[#1a1c1e] w-6 text-right">{issue.count}</span>
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
