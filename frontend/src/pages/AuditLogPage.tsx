import { useEffect, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { apiClient } from "../lib/apiClient";

interface AuditEntry {
  id: string;
  action: string;
  detail: string;
  userName: string;
  created_at: string;
}

interface NotifEntry {
  id: string;
  recipientName: string;
  message: string;
  success: boolean;
  created_at: string;
}

const ACTION_LABELS: Record<string, string> = {
  assign: "Penugasan",
  upload: "Unggah",
  edit_user: "Edit Pengguna",
  delete_user: "Hapus Pengguna",
  change_password: "Ubah Kata Sandi",
};

export function AuditLogPage() {
  const [tab, setTab] = useState<"audit" | "notifications">("audit");
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [notifs, setNotifs] = useState<NotifEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.get("/audit/logs?limit=100"),
      apiClient.get("/audit/notifications?limit=100"),
    ])
      .then(([logRes, notifRes]) => {
        setLogs(logRes.data);
        setNotifs(notifRes.data);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <div className="space-y-8">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-black dark:text-white">
          Log Audit
        </h1>

        <div className="flex gap-0 border border-gray-200 dark:border-slate-600">
          {(["audit", "notifications"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-3 text-[10px] font-semibold uppercase tracking-wide transition ${
                tab === t
                  ? "bg-[#E81E28] text-white"
                  : "bg-white text-slate-500 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-400"
              }`}
            >
              {t === "audit" ? "Log Aktivitas" : "Notifikasi"}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="py-16 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            Memuat...
          </p>
        ) : tab === "audit" ? (
          <div className="border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800">
            {logs.length === 0 ? (
              <p className="px-6 py-16 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">
                Belum ada aktivitas tercatat.
              </p>
            ) : (
              logs.map((log, i) => (
                <div
                  key={log.id}
                  className={`px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 ${
                    i > 0 ? "border-t border-slate-200 dark:border-slate-700" : ""
                  }`}
                >
                  <span className="text-[9px] font-semibold uppercase tracking-wider bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-1 rounded w-fit">
                    {ACTION_LABELS[log.action] || log.action}
                  </span>
                  <span className="text-xs font-bold text-[#1a1c1e] dark:text-white flex-1">
                    {log.detail}
                  </span>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400 shrink-0">
                    {log.userName}
                  </span>
                  <span className="text-[9px] text-slate-400 shrink-0">
                    {new Date(log.created_at).toLocaleString("id-ID", {
                      day: "2-digit", month: "short", year: "numeric",
                      hour: "2-digit", minute: "2-digit",
                    })}
                  </span>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800">
            {notifs.length === 0 ? (
              <p className="px-6 py-16 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">
                Belum ada notifikasi terkirim.
              </p>
            ) : (
              notifs.map((n, i) => (
                <div
                  key={n.id}
                  className={`px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4 ${
                    i > 0 ? "border-t border-slate-200 dark:border-slate-700" : ""
                  }`}
                >
                  <span
                    className={`text-[9px] font-semibold uppercase tracking-wider px-2 py-1 rounded w-fit ${
                      n.success
                        ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                        : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                    }`}
                  >
                    {n.success ? "Terkirim" : "Gagal"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-bold text-slate-600 dark:text-slate-300">
                      Ke: {n.recipientName}
                    </p>
                    <p className="text-xs text-[#1a1c1e] dark:text-white mt-1 line-clamp-2 whitespace-pre-line">
                      {n.message}
                    </p>
                  </div>
                  <span className="text-[9px] text-slate-400 shrink-0">
                    {new Date(n.created_at).toLocaleString("id-ID", {
                      day: "2-digit", month: "short", year: "numeric",
                      hour: "2-digit", minute: "2-digit",
                    })}
                  </span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
