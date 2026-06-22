import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { getUsers, createUser, updateUser, deleteUser } from "../services/userService";
import { getDashboardSnapshot } from "../services/dashboardService";
import { apiClient } from "../lib/apiClient";
import type { User, UserBase } from "../types/user";
import type { Target } from "../types/target";

type PendingAction = { type: "edit"; user: User } | { type: "delete"; user: User };

export function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [name, setName] = useState("");
  const [telegramId, setTelegramId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editName, setEditName] = useState("");
  const [editTelegramId, setEditTelegramId] = useState("");
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [userData, snap] = await Promise.all([
        getUsers(),
        getDashboardSnapshot(),
      ]);
      setUsers(userData);
      setTargets(snap.targets);
    } catch (err) {
      console.error("Gagal memuat data:", err);
    } finally {
      setIsLoading(false);
    }
  }

  function getOfficerStats(userId: string) {
    const assigned = targets.filter(t => t.assignedOfficer === userId);
    const completed = assigned.filter(t => t.status === "completed").length;
    const inProgress = assigned.filter(t => t.status === "in_progress").length;
    return { assigned: assigned.length, completed, inProgress };
  }

  const filteredUsers = useMemo(() => {
    if (!query) return users;
    const q = query.toLowerCase();
    return users.filter(u =>
      u.name.toLowerCase().includes(q) ||
      (u.telegram_id || "").includes(q)
    );
  }, [users, query]);

  const officers = (users || []).filter(u => u.role === "officer");
  const managers = (users || []).filter(u => u.role === "manager");
  const linked = (users || []).filter(u => u.telegram_id).length;

  function formatRole(role: string) {
    return role === "manager" ? "Manajer" : "Petugas";
  }

  async function handleAddUser(e: React.FormEvent) {
    e.preventDefault();
    if (!name) return;

    setIsSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: UserBase = {
        name,
        telegram_id: telegramId || undefined,
        role: "officer",
      };
      const created = await createUser(payload);
      setName("");
      setTelegramId("");
      setSuccess(`${created.name} berhasil didaftarkan.`);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Gagal menambahkan pengguna.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function requestEdit(user: User) {
    setPendingAction({ type: "edit", user });
    setConfirmPassword("");
    setPasswordError(null);
  }

  function requestDelete(user: User) {
    setPendingAction({ type: "delete", user });
    setConfirmPassword("");
    setPasswordError(null);
  }

  async function handlePasswordConfirm(e: React.FormEvent) {
    e.preventDefault();
    if (!pendingAction || !confirmPassword) return;
    setIsVerifying(true);
    setPasswordError(null);
    try {
      await apiClient.post("/auth/verify-password", { password: confirmPassword });
      const action = pendingAction;
      setPendingAction(null);
      setConfirmPassword("");
      if (action.type === "edit") {
        setEditingUser(action.user);
        setEditName(action.user.name);
        setEditTelegramId(action.user.telegram_id || "");
      } else {
        try {
          await deleteUser(action.user.id);
          loadData();
        } catch {
          alert("Gagal menghapus pengguna.");
        }
      }
    } catch {
      setPasswordError("Kata sandi tidak valid.");
    } finally {
      setIsVerifying(false);
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!editingUser) return;
    try {
      await updateUser(editingUser.id, {
        name: editName,
        telegram_id: editTelegramId || undefined,
      });
      setEditingUser(null);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal memperbarui pengguna.");
    }
  }

  return (
    <AppShell>
      <div className="space-y-12 font-sans">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-black">
            Direktori Personel
          </h1>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            {users.length} Total &middot; {officers.length} Petugas &middot; {managers.length} Manajer
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
          {/* Main Directory */}
          <section className="min-w-0">
            <div className="border-b-2 border-gray-200 pb-2 mb-6 flex items-center justify-between">
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-500">Personel Terdaftar</h2>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Cari nama atau ID..."
                className="w-52 border-b border-gray-200 bg-transparent px-1 py-1 text-[10px] font-bold uppercase tracking-wider outline-none placeholder:text-slate-300"
              />
            </div>

            {isLoading ? (
              <p className="py-16 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Memuat data personel...
              </p>
            ) : filteredUsers.length === 0 ? (
              <p className="py-16 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                {query ? "Data tidak ditemukan." : "Belum ada personel terdaftar."}
              </p>
            ) : (
              <div className="border border-gray-200 bg-white overflow-x-auto overflow-hidden">
                {/* Table header */}
                <div className="min-w-[560px] grid grid-cols-[1fr_80px_100px_60px_60px_100px] gap-0 border-b-2 border-gray-200 bg-[#f8f8f6] px-6 py-3 text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                  <span>Nama</span>
                  <span>Peran</span>
                  <span>Telegram</span>
                  <span className="text-center">Tugas</span>
                  <span className="text-center">Selesai</span>
                  <span className="text-center" />
                </div>

                {/* Rows */}
                {filteredUsers.map((user, i) => {
                  const stats = getOfficerStats(user.id);
                  return (
                    <div
                      key={user.id}
                      className={`min-w-[560px] grid grid-cols-[1fr_80px_100px_60px_60px_100px] gap-0 items-center px-6 py-3 ${
                        i > 0 ? "border-t border-slate-200" : ""
                      }`}
                    >
                      <div>
                        <p className="text-xs font-bold text-[#1a1c1e]">{user.name}</p>
                        <p className="text-[9px] text-slate-400 mt-0.5">
                          {new Date(user.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                        </p>
                      </div>
                      <span className={`text-[9px] font-semibold uppercase tracking-wider ${
                        user.role === "manager" ? "text-slate-700" : "text-slate-400"
                      }`}>
                        {formatRole(user.role)}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        {user.telegram_id || <span className="text-slate-300">&mdash;</span>}
                      </span>
                      <span className="text-center text-xs font-bold text-[#1a1c1e]">
                        {stats.assigned || <span className="text-slate-300">&mdash;</span>}
                      </span>
                      <span className="text-center text-xs font-bold text-green-700">
                        {stats.completed || <span className="text-slate-300">&mdash;</span>}
                      </span>
                      <span className="text-center flex gap-2 justify-center">
                        <button
                          onClick={() => requestEdit(user)}
                          className="text-[9px] text-blue-600 font-semibold uppercase tracking-wider hover:underline"
                        >
                          Ubah
                        </button>
                        <button
                          onClick={() => requestDelete(user)}
                          className="text-[9px] text-red-600 font-semibold uppercase tracking-wider hover:underline"
                        >
                          Hapus
                        </button>
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Telegram link status */}
            {users.length > 0 && (
              <div className="mt-6 flex items-center gap-6 text-[9px] font-bold uppercase tracking-wider text-slate-400">
                <span>{linked} dari {users.length} terhubung ke Telegram</span>
                {users.length - linked > 0 && (
                  <span className="text-amber-600">
                    {users.length - linked} belum terhubung &mdash; tidak dapat menerima notifikasi
                  </span>
                )}
              </div>
            )}
          </section>

          {/* Sidebar: Registration */}
          <section>
            <div className="border-b-2 border-gray-200 pb-2 mb-6">
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-500">Daftarkan Petugas</h2>
            </div>

            <form onSubmit={handleAddUser} className="border border-gray-200 bg-white p-6 space-y-5">
              <div className="space-y-1.5">
                <label className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-400">Nama Lengkap *</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Masukkan nama petugas"
                  className="w-full border-b border-gray-200 bg-transparent px-0 py-2 text-sm font-bold outline-none placeholder:text-slate-300 focus:border-b-2"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-400">Telegram ID</label>
                <input
                  value={telegramId}
                  onChange={(e) => setTelegramId(e.target.value)}
                  placeholder="mis. 123456789"
                  className="w-full border-b border-gray-200 bg-transparent px-0 py-2 text-sm font-bold font-mono outline-none placeholder:text-slate-300 focus:border-b-2"
                />
                <p className="text-[9px] text-slate-400">
                  Diperlukan untuk akses Mini App dan notifikasi.
                </p>
              </div>

              {error && <p className="text-[10px] font-bold text-red-600">{error}</p>}
              {success && <p className="text-[10px] font-bold text-green-700">{success}</p>}

              <button
                disabled={isSubmitting || !name}
                className="w-full border-2 border-gray-200 bg-black py-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-white transition hover:bg-white hover:text-black disabled:opacity-30"
              >
                {isSubmitting ? "Memproses..." : "Daftar"}
              </button>
            </form>

            {/* Quick Stats */}
            <div className="mt-8 space-y-3">
              <div className="border-b-2 border-gray-200 pb-2 mb-4">
                <h2 className="text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-500">Ringkasan</h2>
              </div>
              <Row label="Total Personel" value={users.length} />
              <Row label="Petugas Lapangan" value={officers.length} />
              <Row label="Manajer" value={managers.length} />
              <Row label="Terhubung Telegram" value={linked} total={users.length} />
            </div>
          </section>
        </div>
      </div>

      {/* Password Confirmation Modal */}
      {pendingAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setPendingAction(null)}>
          <form
            onSubmit={handlePasswordConfirm}
            onClick={e => e.stopPropagation()}
            className="bg-white rounded-2xl border border-gray-100 w-full max-w-xs mx-4 p-6 space-y-5"
          >
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wide">Konfirmasi Kata Sandi</h2>
              <p className="text-[10px] text-slate-500 mt-2">
                Masukkan kata sandi Anda untuk {pendingAction.type === "edit" ? "mengubah" : "menghapus"}{" "}
                <span className="font-bold text-[#1a1c1e]">{pendingAction.user.name}</span>
              </p>
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-400">Kata Sandi</label>
              <input
                type="password"
                autoFocus
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                className="w-full border-b border-gray-200 bg-transparent px-0 py-2 text-sm font-bold outline-none focus:border-b-2"
              />
              {passwordError && <p className="text-[10px] font-bold text-red-600">{passwordError}</p>}
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={!confirmPassword || isVerifying}
                className="flex-1 bg-[#E81E28] text-white py-2.5 text-[10px] font-semibold uppercase tracking-wide hover:bg-[#c8161f] disabled:opacity-30"
              >
                {isVerifying ? "Memverifikasi..." : "Konfirmasi"}
              </button>
              <button
                type="button"
                onClick={() => setPendingAction(null)}
                className="flex-1 border border-gray-200 py-2.5 text-[10px] font-semibold uppercase tracking-wide hover:bg-slate-100"
              >
                Batal
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Edit Modal */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setEditingUser(null)}>
          <form
            onSubmit={handleUpdate}
            onClick={e => e.stopPropagation()}
            className="bg-white rounded-2xl border border-gray-100 w-full max-w-sm mx-4 p-6 space-y-5"
          >
            <h2 className="text-xs font-semibold uppercase tracking-wide">Ubah {editingUser.name}</h2>
            <div className="space-y-1.5">
              <label className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-400">Nama</label>
              <input
                value={editName}
                onChange={e => setEditName(e.target.value)}
                className="w-full border-b border-gray-200 bg-transparent px-0 py-2 text-sm font-bold outline-none focus:border-b-2"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-400">Telegram ID</label>
              <input
                value={editTelegramId}
                onChange={e => setEditTelegramId(e.target.value)}
                placeholder="mis. 123456789"
                className="w-full border-b border-gray-200 bg-transparent px-0 py-2 text-sm font-bold font-mono outline-none focus:border-b-2"
              />
            </div>
            <div className="flex gap-3">
              <button type="submit" className="flex-1 bg-[#E81E28] text-white py-2.5 text-[10px] font-semibold uppercase tracking-wide hover:bg-[#c8161f]">
                Simpan
              </button>
              <button type="button" onClick={() => setEditingUser(null)} className="flex-1 border border-gray-200 py-2.5 text-[10px] font-semibold uppercase tracking-wide hover:bg-slate-100">
                Batal
              </button>
            </div>
          </form>
        </div>
      )}
    </AppShell>
  );
}

function Row({ label, value, total }: { label: string; value: number; total?: number }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-200 pb-2">
      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{label}</span>
      <span className="text-sm font-medium text-[#1a1c1e]">
        {value}{total !== undefined && <span className="text-slate-400 text-xs"> / {total}</span>}
      </span>
    </div>
  );
}
