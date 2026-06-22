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
        <div className="py-24 text-center text-sm font-medium text-gray-400">Memuat dasbor…</div>
      </AppShell>
    );
  }

  if (error || !snapshot) {
    return (
      <AppShell activeTab="DASHBOARD">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm font-medium text-[#E81E28]">
          {error || "Gagal memuat data."}
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
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Dasbor Operasional</h1>
          <p className="mt-1 text-sm text-gray-500">Ringkasan real-time target penagihan dan aktivitas lapangan.</p>
        </div>

        {/* Summary Cards */}
        <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <SummaryCard label="Total Target" value={stats.totalTargets} accent="default" />
          <SummaryCard label="Selesai" value={stats.completed} accent="success" />
          <SummaryCard label="Sedang Berjalan" value={stats.inProgress} accent="warning" />
          <SummaryCard label="Menunggu" value={stats.pending} accent="danger" />
        </section>

        {/* Operational Panels: Pending / Active / Comments */}
        <section className="grid gap-5 lg:grid-cols-3">
          {/* Unassigned Targets (Action Required) */}
          <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
              <h3 className="text-sm font-semibold text-gray-900">Perlu Penugasan</h3>
              <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-[#E81E28]">{pendingTargets.length}</span>
            </div>
            <div className="max-h-[320px] divide-y divide-gray-100 overflow-y-auto">
              {pendingTargets.length === 0 ? (
                <p className="px-5 py-8 text-center text-xs text-gray-400">Semua target sudah ditugaskan</p>
              ) : (
                pendingTargets.slice(0, 8).map(t => (
                  <div key={t.id} className="px-5 py-3">
                    <p className="text-sm font-medium text-gray-900">{t.customerName}</p>
                    <p className="mt-0.5 truncate text-xs text-gray-400">{t.address}</p>
                    <p className="mt-1 text-sm font-semibold text-[#E81E28]">{formatCurrency(t.amountDue)}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recently Assigned (In Progress) */}
          <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
              <h3 className="text-sm font-semibold text-gray-900">Penugasan Aktif</h3>
              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-600">{stats.inProgress}</span>
            </div>
            <div className="max-h-[320px] divide-y divide-gray-100 overflow-y-auto">
              {recentAssigned.length === 0 ? (
                <p className="px-5 py-8 text-center text-xs text-gray-400">Tidak ada penugasan aktif</p>
              ) : (
                recentAssigned.map(t => (
                  <div key={t.id} className="px-5 py-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-900">{t.customerName}</p>
                      <p className="text-xs font-semibold text-amber-600">{formatCurrency(t.amountDue)}</p>
                    </div>
                    <p className="mt-0.5 text-xs text-gray-500">
                      Petugas: <span className="font-medium text-gray-700">{getOfficerName(t.assignedOfficer)}</span>
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Officer Comments */}
          <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
              <h3 className="text-sm font-semibold text-gray-900">Masukan Petugas</h3>
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-500">{recentComments.length}</span>
            </div>
            <div className="max-h-[320px] divide-y divide-gray-100 overflow-y-auto">
              {recentComments.length === 0 ? (
                <p className="px-5 py-8 text-center text-xs text-gray-400">Belum ada komentar</p>
              ) : (
                recentComments.map(c => (
                  <div key={c.id} className="px-5 py-3">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="text-xs font-medium text-gray-700">{c.officerName}</span>
                      {c.tag && (
                        <span className="rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-medium text-[#E81E28]">
                          {TAG_LABELS[c.tag] || c.tag}
                        </span>
                      )}
                    </div>
                    <p className="truncate text-xs text-gray-400">{c.customerName}</p>
                    <p className="mt-0.5 line-clamp-2 text-sm text-gray-700">{c.message}</p>
                    <p className="mt-1 text-[11px] text-gray-400">
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
        <section className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
            <h3 className="text-sm font-semibold text-gray-900">Petugas Aktif</h3>
            <span className="text-xs text-gray-400">{officers.length} terdaftar</span>
          </div>
          <div className="grid grid-cols-3 gap-px bg-gray-100 lg:grid-cols-6">
            {officers.map(o => {
              const assigned = targets.filter(t => t.assignedOfficer === o.id).length;
              const completed = targets.filter(t => t.assignedOfficer === o.id && t.status === "completed").length;
              return (
                <div key={o.id} className="bg-white px-4 py-5 text-center">
                  <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-500">
                    {o.name.split(" ").map(n => n[0]).join("").slice(0, 2)}
                  </div>
                  <p className="truncate text-xs font-medium text-gray-900">{o.name}</p>
                  <p className="mt-1 text-[11px] text-gray-400">{assigned} ditugaskan · {completed} selesai</p>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
