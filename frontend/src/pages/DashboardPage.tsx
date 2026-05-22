import { useEffect, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { SummaryCard } from "../components/dashboard/SummaryCard";
import { getDashboardSnapshot } from "../services/dashboardService";
import { apiClient } from "../lib/apiClient";
import { formatCurrency } from "../lib/format";
import type { DashboardSnapshot } from "../types/dashboard";

import type { User } from "../types/user";
import { getUsers } from "../services/userService";
interface Comment {
  id: string;
  message: string;
  tag: string | null;
  officerName: string;
  created_at: string;
}

const TAG_LABELS: Record<string, string> = {
  wrong_address: "Alamat Salah",
  wrong_phone: "Nomor Salah",
  customer_moved: "Customer Pindah",
  not_found: "Tidak Ditemukan",
  other: "Lainnya",
};

export function DashboardPage() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [recentComments, setRecentComments] = useState<(Comment & { customerName: string })[]>([]);

  useEffect(() => {
    let isMounted = true;

    Promise.all([
      getDashboardSnapshot(),
      getUsers(),
    ])
      .then(async ([snap, users]) => {
        if (!isMounted) return;
        setSnapshot(snap);
        setAllUsers(users);

        // Fetch recent comments in one call (no N+1)
        try {
          const cmtRes = await apiClient.get("/dashboard/recent-comments?limit=5");
          const cmtData = cmtRes.data;
          setRecentComments(Array.isArray(cmtData) ? cmtData : []);
        } catch {
          setRecentComments([]);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || "Failed to load dashboard data.");
      })
      .finally(() => {
        if (!isMounted) return;
        setIsLoading(false);
      });
    const interval = setInterval(() => {
      Promise.all([getDashboardSnapshot(), getUsers()])
        .then(async ([snap, users]) => {
          if (!isMounted) return;
          setSnapshot(snap);
          setAllUsers(users);
        })
        .catch(() => {});
    }, 10000);

    return () => { isMounted = false; clearInterval(interval); };
  }, []);

  function getOfficerName(officerId: string | null): string {
    if (!officerId) return "—";
    const user = allUsers.find(u => u.id === officerId);
    return user?.name ?? officerId.slice(0, 8);
  }

  if (isLoading) {
    return (
      <AppShell activeTab="DASHBOARD">
        <div className="py-20 text-center text-sm font-bold uppercase tracking-widest text-slate-400">
          Initializing System Data...
        </div>
      </AppShell>
    );
  }

  if (error || !snapshot) {
    return (
      <AppShell activeTab="DASHBOARD">
        <div className="rounded-lg bg-red-50 p-6 text-center text-sm font-bold text-red-600">
          {error || "Failed to load data."}
        </div>
      </AppShell>
    );
  }

  const { stats } = snapshot;
  const targets = Array.isArray(snapshot.targets) ? snapshot.targets : [];

  const pendingTargets = targets.filter(t => t.status === "pending");
  const recentAssigned = targets
    .filter(t => t.status === "in_progress")
    .slice(0, 5);

  const officers = (allUsers || []).filter(u => u.role === "officer");

  return (
    <AppShell activeTab="DASHBOARD">
      <div className="space-y-10">
        <h1 className="font-serif text-3xl font-medium tracking-wide uppercase text-black">
          Operational Dashboard
        </h1>

        {/* Summary Cards */}
        <section className="grid gap-0 border-l border-t border-black grid-cols-2 lg:grid-cols-4">
          <SummaryCard label="Total Targets" value={stats.totalTargets} accent="default" />
          <SummaryCard label="Completed" value={stats.completed} accent="success" />
          <SummaryCard label="In Progress" value={stats.inProgress} accent="warning" />
          <SummaryCard label="Pending" value={stats.pending} accent="danger" />
        </section>

        {/* Operational Panels: Pending / Active / Comments */}
        <section className="grid gap-6 lg:grid-cols-3">
          {/* Unassigned Targets (Action Required) */}
          <div className="border border-black bg-white">
            <div className="bg-red-50 border-b border-black px-6 py-4 flex items-center justify-between">
              <h3 className="text-xs font-black uppercase tracking-widest text-red-700">
                Needs Assignment
              </h3>
              <span className="text-xs font-black text-red-600">{pendingTargets.length}</span>
            </div>
            <div className="divide-y divide-slate-100 max-h-[320px] overflow-y-auto">
              {pendingTargets.length === 0 ? (
                <p className="px-6 py-8 text-center text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  All targets assigned
                </p>
              ) : (
                pendingTargets.slice(0, 8).map(t => (
                  <div key={t.id} className="px-6 py-3">
                    <p className="text-xs font-bold text-[#1a1c1e]">{t.customerName}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5 truncate">{t.address}</p>
                    <p className="text-xs font-black text-red-600 mt-1">{formatCurrency(t.amountDue)}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recently Assigned (In Progress) */}
          <div className="border border-black bg-white">
            <div className="bg-amber-50 border-b border-black px-6 py-4 flex items-center justify-between">
              <h3 className="text-xs font-black uppercase tracking-widest text-amber-700">
                Active Assignments
              </h3>
              <span className="text-xs font-black text-amber-600">{stats.inProgress}</span>
            </div>
            <div className="divide-y divide-slate-100 max-h-[320px] overflow-y-auto">
              {recentAssigned.length === 0 ? (
                <p className="px-6 py-8 text-center text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  No active assignments
                </p>
              ) : (
                recentAssigned.map(t => (
                  <div key={t.id} className="px-6 py-3">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-bold text-[#1a1c1e]">{t.customerName}</p>
                      <p className="text-[10px] font-black text-amber-600">{formatCurrency(t.amountDue)}</p>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      Officer: <span className="font-bold">{getOfficerName(t.assignedOfficer)}</span>
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Officer Comments */}
          <div className="border border-black bg-white">
            <div className="bg-slate-50 border-b border-black px-6 py-4 flex items-center justify-between">
              <h3 className="text-xs font-black uppercase tracking-widest text-slate-700">
                Officer Feedback
              </h3>
              <span className="text-xs font-black text-slate-500">{recentComments.length}</span>
            </div>
            <div className="divide-y divide-slate-100 max-h-[320px] overflow-y-auto">
              {recentComments.length === 0 ? (
                <p className="px-6 py-8 text-center text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  No comments yet
                </p>
              ) : (
                recentComments.map(c => (
                  <div key={c.id} className="px-6 py-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-bold text-slate-600">{c.officerName}</span>
                      {c.tag && (
                        <span className="text-[8px] font-black uppercase tracking-wider bg-red-100 text-red-600 px-1.5 py-0.5 rounded">
                          {TAG_LABELS[c.tag] || c.tag}
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-slate-500 truncate">{c.customerName}</p>
                    <p className="text-[11px] text-[#1a1c1e] mt-0.5 line-clamp-2">{c.message}</p>
                    <p className="text-[9px] text-slate-400 mt-1">
                      {new Date(c.created_at).toLocaleString("id-ID", {
                        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
                      })}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        {/* Officer Quick View */}
        <section className="border border-black bg-white">
          <div className="bg-[#f2f2f2] border-b border-black px-4 sm:px-6 py-4 flex items-center justify-between">
            <h3 className="text-xs font-black uppercase tracking-widest text-black">Active Officers</h3>
            <span className="text-xs font-black text-slate-500">{officers.length} registered</span>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-3 lg:grid-cols-6 divide-x divide-slate-100">
            {officers.map(o => {
              const assigned = targets.filter(t => t.assignedOfficer === o.id).length;
              const completed = targets.filter(t => t.assignedOfficer === o.id && t.status === "completed").length;
              return (
                <div key={o.id} className="px-5 py-4 text-center">
                  <div className="w-10 h-10 rounded-full bg-slate-200 mx-auto mb-2 flex items-center justify-center text-xs font-black text-slate-500">
                    {o.name.split(" ").map(n => n[0]).join("").slice(0, 2)}
                  </div>
                  <p className="text-[10px] font-bold text-[#1a1c1e] truncate">{o.name}</p>
                  <p className="text-[9px] text-slate-400 mt-1">
                    {assigned} assigned · {completed} done
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
