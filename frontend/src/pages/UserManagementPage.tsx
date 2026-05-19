import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { getUsers, createUser, deleteUser } from "../services/userService";
import { getDashboardSnapshot } from "../services/dashboardService";
import type { User, UserBase } from "../types/user";
import type { Target } from "../types/target";

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
      console.error("Failed to load data:", err);
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

  const officers = users.filter(u => u.role === "officer");
  const managers = users.filter(u => u.role === "manager");
  const linked = users.filter(u => u.telegram_id).length;

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
      setSuccess(`${created.name} registered successfully.`);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to add user.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(user: User) {
    const stats = getOfficerStats(user.id);
    const extra = stats.assigned > 0
      ? `\n\nThis officer has ${stats.assigned} assigned target(s). They will become unassigned.`
      : "";
    if (!confirm(`Remove ${user.name}?${extra}`)) return;
    try {
      await deleteUser(user.id);
      loadData();
    } catch (err) {
      alert("Failed to delete user.");
    }
  }

  return (
    <AppShell>
      <div className="space-y-12 font-sans">
        <div className="flex items-end justify-between">
          <h1 className="font-serif text-3xl font-medium tracking-wide uppercase text-black">
            Personnel Directory
          </h1>
          <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
            {users.length} Total &middot; {officers.length} Officers &middot; {managers.length} Managers
          </p>
        </div>

        <div className="grid gap-12 lg:grid-cols-[1fr_340px]">
          {/* Main Directory */}
          <section>
            <div className="border-b-2 border-black pb-2 mb-6 flex items-center justify-between">
              <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500">Registered Personnel</h2>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search name or ID..."
                className="w-52 border-b border-black bg-transparent px-1 py-1 text-[10px] font-bold uppercase tracking-wider outline-none placeholder:text-slate-300"
              />
            </div>

            {isLoading ? (
              <p className="py-16 text-center text-[10px] font-black uppercase tracking-widest text-slate-400">
                Loading Personnel Records...
              </p>
            ) : filteredUsers.length === 0 ? (
              <p className="py-16 text-center text-[10px] font-black uppercase tracking-widest text-slate-400">
                {query ? "No matching records." : "No registered personnel."}
              </p>
            ) : (
              <div className="border border-black bg-white">
                {/* Table header */}
                <div className="grid grid-cols-[1fr_80px_100px_60px_60px_60px] gap-0 border-b-2 border-black bg-[#f8f8f6] px-6 py-3 text-[9px] font-black uppercase tracking-[0.2em] text-slate-500">
                  <span>Name</span>
                  <span>Role</span>
                  <span>Telegram</span>
                  <span className="text-center">Asgn</span>
                  <span className="text-center">Done</span>
                  <span className="text-center" />
                </div>

                {/* Rows */}
                {filteredUsers.map((user, i) => {
                  const stats = getOfficerStats(user.id);
                  return (
                    <div
                      key={user.id}
                      className={`grid grid-cols-[1fr_80px_100px_60px_60px_60px] gap-0 items-center px-6 py-3 ${
                        i > 0 ? "border-t border-slate-200" : ""
                      }`}
                    >
                      <div>
                        <p className="text-xs font-bold text-[#1a1c1e]">{user.name}</p>
                        <p className="text-[9px] text-slate-400 mt-0.5">
                          {new Date(user.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                        </p>
                      </div>
                      <span className={`text-[9px] font-black uppercase tracking-wider ${
                        user.role === "manager" ? "text-slate-700" : "text-slate-400"
                      }`}>
                        {user.role}
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
                      <span className="text-center">
                        <button
                          onClick={() => handleDelete(user)}
                          className="text-[9px] text-red-600 font-black uppercase tracking-wider hover:underline"
                        >
                          Remove
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
                <span>{linked} of {users.length} linked to Telegram</span>
                {users.length - linked > 0 && (
                  <span className="text-amber-600">
                    {users.length - linked} unlinked &mdash; cannot receive notifications
                  </span>
                )}
              </div>
            )}
          </section>

          {/* Sidebar: Registration */}
          <section>
            <div className="border-b-2 border-black pb-2 mb-6">
              <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500">Register Officer</h2>
            </div>

            <form onSubmit={handleAddUser} className="border border-black bg-white p-6 space-y-5">
              <div className="space-y-1.5">
                <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">Full Name *</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter officer name"
                  className="w-full border-b border-black bg-transparent px-0 py-2 text-sm font-bold outline-none placeholder:text-slate-300 focus:border-b-2"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">Telegram ID</label>
                <input
                  value={telegramId}
                  onChange={(e) => setTelegramId(e.target.value)}
                  placeholder="e.g. 123456789"
                  className="w-full border-b border-black bg-transparent px-0 py-2 text-sm font-bold font-mono outline-none placeholder:text-slate-300 focus:border-b-2"
                />
                <p className="text-[9px] text-slate-400">
                  Required for Mini App access and notifications.
                </p>
              </div>

              {error && <p className="text-[10px] font-bold text-red-600">{error}</p>}
              {success && <p className="text-[10px] font-bold text-green-700">{success}</p>}

              <button
                disabled={isSubmitting || !name}
                className="w-full border-2 border-black bg-black py-3 text-[10px] font-black uppercase tracking-[0.2em] text-white transition hover:bg-white hover:text-black disabled:opacity-30"
              >
                {isSubmitting ? "Processing..." : "Register"}
              </button>
            </form>

            {/* Quick Stats */}
            <div className="mt-8 space-y-3">
              <div className="border-b-2 border-black pb-2 mb-4">
                <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500">Summary</h2>
              </div>
              <Row label="Total Personnel" value={users.length} />
              <Row label="Field Officers" value={officers.length} />
              <Row label="Managers" value={managers.length} />
              <Row label="Telegram Linked" value={linked} total={users.length} />
            </div>
          </section>
        </div>
      </div>
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
