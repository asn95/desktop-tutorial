import { useState, useEffect } from "react";
import { formatCurrency, formatStatus } from "../../lib/format";
import type { Target } from "../../types/target";
import type { User } from "../../types/user";
import { getUsers } from "../../services/userService";
import { apiClient } from "../../lib/apiClient";

interface Comment {
  id: string;
  message: string;
  tag: string | null;
  officerName: string;
  created_at: string;
}

interface Report {
  id: string;
  payment_status: string;
  notes: string | null;
  photo_url: string | null;
  officerName: string;
  submitted_at: string;
}

const TAG_LABELS: Record<string, string> = {
  wrong_address: "Alamat Salah",
  wrong_phone: "Nomor Salah",
  customer_moved: "Customer Pindah",
  not_found: "Tidak Ditemukan",
  other: "Lainnya",
};

interface TableProps {
  targets: Target[];
  onRefresh?: () => void;
  selected?: Set<string>;
  onToggleSelect?: (id: string) => void;
  onToggleAll?: () => void;
  pendingCount?: number;
}

export function TargetsTable({ targets, onRefresh, selected, onToggleSelect, onToggleAll, pendingCount }: TableProps) {
  const [officers, setOfficers] = useState<User[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [detailTarget, setDetailTarget] = useState<Target | null>(null);
  const [isAssigning, setIsAssigning] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);

  useEffect(() => {
    getUsers().then(data => {
      setAllUsers(data);
      setOfficers(data.filter(u => u.role === "officer"));
    }).catch(() => {});
  }, []);

  function getOfficerName(officerId: string | null): string {
    if (!officerId) return "—";
    const user = allUsers.find(u => u.id === officerId);
    return user?.name ?? officerId.slice(0, 8);
  }

  async function handleAssign(targetId: string, officerId: string) {
    if (!officerId) return;
    setIsAssigning(true);
    try {
      await apiClient.patch(`/targets/${targetId}/assign?officer_id=${officerId}`);
      setSelectedTarget(null);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert("Gagal menugaskan petugas.");
    } finally {
      setIsAssigning(false);
    }
  }

  async function openDetail(target: Target) {
    setDetailTarget(target);
    setComments([]);
    setReports([]);
    setLoadingComments(true);
    try {
      const [cmtRes, rptRes] = await Promise.all([
        apiClient.get(`/targets/${target.id}/comments`),
        apiClient.get(`/targets/${target.id}/reports`),
      ]);
      setComments(cmtRes.data);
      setReports(Array.isArray(rptRes.data) ? rptRes.data : []);
    } catch {
      setComments([]);
      setReports([]);
    } finally {
      setLoadingComments(false);
    }
  }

  return (
    <>
      <div className="w-full rounded-2xl border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-[640px] w-full text-left text-[11px] font-bold uppercase tracking-wider">
            <thead className="bg-gray-50 text-[#1a1c1e]">
              <tr className="border-b border-gray-200">
                {onToggleSelect && (
                  <th className="px-3 py-4 w-8">
                    <input type="checkbox" checked={selected?.size === pendingCount && (pendingCount ?? 0) > 0} onChange={onToggleAll} />
                  </th>
                )}
                <th className="px-4 py-4">ID</th>
                <th className="px-4 py-4">Nama Pelanggan</th>
                <th className="px-4 py-4">Alamat</th>
                <th className="px-4 py-4">Jumlah Tagihan</th>
                <th className="px-4 py-4">Petugas</th>
                <th className="px-4 py-4">Status</th>
                <th className="px-4 py-4 text-center">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {targets.length === 0 ? (
                <tr>
                  <td colSpan={onToggleSelect ? 8 : 7} className="px-4 py-10 text-center text-[#5e6671] normal-case italic">
                    Tidak ada data.
                  </td>
                </tr>
              ) : (
                targets.map((target) => (
                  <tr key={target.id} className="text-[#1a1c1e] transition hover:bg-slate-50/50">
                    {onToggleSelect && (
                      <td className="px-3 py-4 w-8">
                        {target.status === "pending" ? (
                          <input type="checkbox" checked={selected?.has(target.id) ?? false} onChange={() => onToggleSelect(target.id)} />
                        ) : <span />}
                      </td>
                    )}
                    <td className="px-4 py-4 text-slate-500">{target.id.slice(0, 6).toUpperCase()}</td>
                    <td className="px-4 py-4">{target.customerName}</td>
                    <td className="px-4 py-4 normal-case font-medium text-[#5e6671]">{target.address}</td>
                    <td className="px-4 py-4">{formatCurrency(target.amountDue)}</td>
                    <td className="px-4 py-4">
                      {selectedTarget === target.id ? (
                        <select
                          autoFocus
                          className="border border-gray-200 bg-white px-2 py-1 text-[10px] outline-none"
                          onChange={(e) => handleAssign(target.id, e.target.value)}
                          onBlur={() => setSelectedTarget(null)}
                          disabled={isAssigning}
                        >
                          <option value="">Pilih Petugas</option>
                          {officers.map(o => (
                            <option key={o.id} value={o.id}>{o.name}</option>
                          ))}
                        </select>
                      ) : (
                        <span className="font-semibold text-slate-700">
                          {getOfficerName(target.assignedOfficer)}
                        </span>
                      )}
                    </td>
                    <td className={`px-4 py-4 font-semibold ${
                      target.status === 'completed' ? 'text-green-600' :
                      target.status === 'pending' ? 'text-red-600' :
                      'text-amber-600'
                    }`}>
                      {formatStatus(target.status)}
                    </td>
                    <td className="px-4 py-4 text-center">
                      {!target.assignedOfficer ? (
                        <button
                          onClick={() => setSelectedTarget(target.id)}
                          className="border border-gray-200 px-3 py-1 hover:bg-gray-50 transition"
                        >
                          Tugaskan
                        </button>
                      ) : (
                        <button
                          onClick={() => openDetail(target)}
                          className="border border-gray-200 px-3 py-1 hover:bg-gray-50 transition"
                        >
                          Lihat Detail
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Modal */}
      {detailTarget && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40" onClick={() => setDetailTarget(null)}>
          <div className="bg-white rounded-2xl border border-gray-100 w-full sm:max-w-lg sm:mx-4 p-0 max-h-[92vh] sm:max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between shrink-0">
              <h2 className="text-xs font-semibold uppercase tracking-wide">Detail Target</h2>
              <button onClick={() => setDetailTarget(null)} className="text-lg font-bold hover:text-red-600">&times;</button>
            </div>
            <div className="overflow-y-auto flex-1">
              <div className="px-6 py-6 space-y-4 text-sm">
                <div className="grid grid-cols-[120px_1fr] gap-y-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">ID</span>
                  <span className="font-mono text-xs">{detailTarget.id}</span>

                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Pelanggan</span>
                  <span className="font-bold">{detailTarget.customerName}</span>

                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Telepon</span>
                  <span className="font-medium">{detailTarget.phone || "—"}</span>

                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Alamat</span>
                  <span className="font-medium">{detailTarget.address}</span>

                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Jumlah Tagihan</span>
                  <span className="font-semibold text-red-600">{formatCurrency(detailTarget.amountDue)}</span>

                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Petugas</span>
                  <span className="font-bold">{getOfficerName(detailTarget.assignedOfficer)}</span>

                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Status</span>
                  <span className={`font-semibold uppercase ${
                    detailTarget.status === 'completed' ? 'text-green-600' :
                    detailTarget.status === 'pending' ? 'text-red-600' :
                    'text-amber-600'
                  }`}>{formatStatus(detailTarget.status)}</span>
                </div>
              </div>

              {/* Field Reports Section */}
              {reports.length > 0 && (
                <div className="border-t border-slate-200 px-6 py-5">
                  <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">
                    Laporan Lapangan
                  </h3>
                  <div className="space-y-3">
                    {reports.map(r => (
                      <div key={r.id} className="border border-slate-200 rounded px-4 py-3">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-[10px] font-bold text-slate-600">{r.officerName}</span>
                          <span className="text-[8px] font-semibold uppercase tracking-wider bg-blue-100 text-blue-600 px-2 py-0.5 rounded">
                            {r.payment_status}
                          </span>
                        </div>
                        {r.notes && <p className="text-xs text-slate-700 leading-relaxed mb-2">{r.notes}</p>}
                        {r.photo_url && (
                          <a href={`/api${r.photo_url}`} target="_blank" rel="noopener noreferrer">
                            <img
                              src={`/api${r.photo_url}`}
                              alt="Bukti foto"
                              className="w-full max-h-48 object-cover rounded border border-slate-200 cursor-pointer hover:opacity-90"
                            />
                          </a>
                        )}
                        <p className="text-[9px] text-slate-400 mt-2">
                          {new Date(r.submitted_at).toLocaleString("id-ID", {
                            day: "2-digit", month: "short", year: "numeric",
                            hour: "2-digit", minute: "2-digit"
                          })}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Officer Comments Section */}
              <div className="border-t border-slate-200 px-6 py-5">
                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">
                  Komentar Petugas
                </h3>
                {loadingComments ? (
                  <p className="text-xs text-slate-400 italic">Memuat komentar...</p>
                ) : comments.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">Belum ada komentar dari petugas.</p>
                ) : (
                  <div className="space-y-3">
                    {comments.map(c => (
                      <div key={c.id} className="border border-slate-200 rounded px-4 py-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-bold text-slate-600">{c.officerName}</span>
                          {c.tag && (
                            <span className="text-[8px] font-semibold uppercase tracking-wider bg-red-100 text-red-600 px-2 py-0.5 rounded">
                              {TAG_LABELS[c.tag] || c.tag}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed">{c.message}</p>
                        <p className="text-[9px] text-slate-400 mt-1">
                          {new Date(c.created_at).toLocaleString("id-ID", {
                            day: "2-digit", month: "short", year: "numeric",
                            hour: "2-digit", minute: "2-digit"
                          })}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="border-t border-gray-200 px-6 py-4 shrink-0">
              <button
                onClick={() => setDetailTarget(null)}
                className="w-full bg-[#E81E28] text-white py-2 text-xs font-semibold uppercase tracking-wide hover:bg-[#c8161f] transition"
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
