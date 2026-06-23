import { useState, useEffect } from "react";
import { apiClient } from "../lib/apiClient";
import { formatCurrency } from "../lib/format";
import type { Target } from "../types/target";
import indihomeLogo from "../assets/indihome-logo.png";

type ViewState = "login" | "list" | "detail";

export function OfficerAppPage() {
  const [view, setView] = useState<ViewState>("login");
  const [telegramId, setTelegramId] = useState("");
  const [tasks, setTasks] = useState<Target[]>([]);
  const [selectedTask, setSelectedTarget] = useState<Target | null>(null);
  
  // Telegram SDK
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      
      // Auto-login using Telegram User ID if available
      const user = tg.initDataUnsafe?.user;
      if (user?.id) {
        const tid = String(user.id);
        setTelegramId(tid);
        apiClient.get<Target[]>(`/officer/tasks/${tid}`)
          .then(res => {
            setTasks(res.data);
            setView("list");
          })
          .catch(() => {
            // If not found in our DB, stay on login to show helpful error
          });
      }
    }
  }, []);

  // Handle Telegram Back Button
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp;
    if (!tg) return;

    if (view === "detail") {
      tg.BackButton.show();
      tg.BackButton.onClick(() => {
        setView("list");
        setSelectedTarget(null);
      });
    } else {
      tg.BackButton.hide();
    }

    return () => {
      tg.BackButton.offClick();
    };
  }, [view]);
  const [paymentStatus, setPaymentStatus] = useState("Janji Bayar");
  const [notes, setNotes] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleLogin() {
    if (!telegramId) return;
    try {
      const res = await apiClient.get<Target[]>(`/officer/tasks/${telegramId}`);
      setTasks(res.data);
      setView("list");
    } catch (err) {
      alert("Profil petugas tidak ditemukan. Daftarkan Telegram ID Anda di Portal Admin.");
    }
  }

  async function handleSubmitReport(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedTask || !photo) return;

    setIsSubmitting(true);
    const formData = new FormData();
    formData.append("target_id", selectedTask.id);
    formData.append("telegram_id", telegramId);
    formData.append("payment_status", paymentStatus);
    formData.append("notes", notes);
    formData.append("photo", photo);

    try {
      await apiClient.post("/officer/report", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      alert("Laporan berhasil dikirim!");
      // Back to list
      const res = await apiClient.get<Target[]>(`/officer/tasks/${telegramId}`);
      setTasks(res.data);
      setView("list");
      setSelectedTarget(null);
      setNotes("");
      setPhoto(null);
    } catch (err) {
      alert("Gagal mengirim laporan.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (view === "login") {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-[#f4f5f7] p-6 font-sans">
        <div className="w-full max-w-[400px] rounded-2xl bg-white p-8 shadow-[0_12px_40px_-12px_rgba(15,23,42,0.18)]">
          <div className="mb-8 flex flex-col items-center text-center">
            <img src={indihomeLogo} alt="IndiHome by Telkomsel" className="mb-4 h-9 w-auto object-contain" />
            <div className="text-2xl font-extrabold tracking-tight text-gray-900">
              <span className="text-[#EA0A2C]">C</span>3MR Lapangan
            </div>
            <p className="mt-1 text-sm text-gray-500">Portal petugas — masuk untuk melanjutkan</p>
          </div>
          <div className="space-y-5">
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">Telegram ID</label>
              <input
                value={telegramId}
                onChange={(e) => setTelegramId(e.target.value)}
                placeholder="mis. 123456789"
                className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 placeholder-gray-400 outline-none transition focus:border-[#EA0A2C] focus:ring-2 focus:ring-[#EA0A2C]/20"
              />
            </div>
            <button
              onClick={handleLogin}
              className="w-full rounded-xl bg-[#EA0A2C] py-3.5 text-sm font-semibold text-white shadow-[0_8px_24px_-8px_rgba(234,10,44,0.5)] transition-colors hover:bg-[#C80825] active:scale-[0.98]"
            >
              Masuk
            </button>
            <p className="text-center text-xs text-gray-400">Gunakan Telegram ID yang didaftarkan oleh manajer Anda.</p>
          </div>
        </div>
      </div>
    );
  }

  if (view === "list") {
    return (
      <div className="min-h-[100dvh] bg-[#f4f5f7] font-sans pb-10">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white/90 px-5 py-4 backdrop-blur">
          <div className="flex items-center gap-2">
            <img src={indihomeLogo} alt="IndiHome by Telkomsel" className="h-6 w-auto object-contain" />
            <span className="text-lg font-extrabold tracking-tight"><span className="text-[#EA0A2C]">C</span>3MR</span>
          </div>
          <span className="rounded-full bg-[#EA0A2C]/10 px-3 py-1 text-xs font-semibold text-[#EA0A2C]">Petugas</span>
        </header>

        <div className="space-y-5 p-5">
          <h2 className="text-xl font-bold tracking-tight text-gray-900">Tugas Saya</h2>
          <div className="space-y-3">
            {tasks.length === 0 ? (
              <p className="py-12 text-center text-sm text-gray-400">Belum ada tugas.</p>
            ) : (
              tasks.map(task => (
                <div
                  key={task.id}
                  onClick={() => { setSelectedTarget(task); setView("detail"); }}
                  className="cursor-pointer rounded-2xl border border-gray-100 bg-white p-5 shadow-[0_2px_16px_-6px_rgba(16,24,40,0.12)] transition-all duration-200 active:scale-[0.99]"
                >
                  <div className="mb-3 flex items-start justify-between">
                    <span className="text-xs font-medium uppercase tracking-wide text-gray-400">#{task.id.slice(0, 6)}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                      task.status === 'completed' ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'
                    }`}>
                      {task.status}
                    </span>
                  </div>
                  <h3 className="font-semibold text-gray-900">{task.customerName}</h3>
                  <p className="mt-0.5 line-clamp-1 text-xs text-gray-400">{task.address}</p>
                  <div className="mt-3 text-lg font-bold text-[#EA0A2C]">{formatCurrency(task.amountDue)}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    );
  }

  if (view === "detail" && selectedTask) {
    return (
      <div className="min-h-[100dvh] bg-white font-sans pb-10">
        <header className="flex items-center gap-3 px-5 py-4">
          <button onClick={() => setView("list")} className="flex h-9 w-9 items-center justify-center rounded-full text-gray-500 transition-colors hover:bg-gray-100">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" /></svg>
          </button>
          <div className="text-sm font-semibold text-gray-500">Detail Tugas</div>
        </header>

        <div className="space-y-8 px-5">
          <section>
            <h2 className="text-2xl font-bold leading-tight tracking-tight text-gray-900">{selectedTask.customerName}</h2>
            <p className="mt-1 text-sm leading-relaxed text-gray-500">{selectedTask.address}</p>
            <div className="mt-5 inline-block rounded-xl bg-red-50 px-4 py-2 text-xl font-bold text-[#EA0A2C]">
              {formatCurrency(selectedTask.amountDue)}
            </div>
          </section>

          <div className="h-px bg-gray-100" />

          <form onSubmit={handleSubmitReport} className="space-y-6">
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">Status penagihan</label>
              <select
                value={paymentStatus}
                onChange={(e) => setPaymentStatus(e.target.value)}
                className="w-full appearance-none rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-[#EA0A2C] focus:ring-2 focus:ring-[#EA0A2C]/20"
              >
                <option>Janji Bayar</option>
                <option>Lunas</option>
                <option>Menolak</option>
                <option>Tidak di Rumah</option>
                <option>Bayar Sebagian</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">Catatan kunjungan</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 placeholder-gray-400 outline-none transition focus:border-[#EA0A2C] focus:ring-2 focus:ring-[#EA0A2C]/20"
                placeholder="Jelaskan hasil kunjungan…"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">Bukti foto</label>
              <label className="flex h-32 w-full cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-200 bg-gray-50 transition-colors hover:bg-gray-100">
                <div className="text-center">
                  <svg className="mx-auto mb-2 h-7 w-7 text-gray-400" fill="none" stroke="currentColor" strokeWidth="1.6" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                  <p className="text-xs font-medium text-gray-500">{photo ? photo.name : "Ketuk untuk ambil foto"}</p>
                </div>
                <input type="file" className="hidden" accept="image/*" capture="environment" onChange={(e) => setPhoto(e.target.files?.[0] || null)} />
              </label>
            </div>

            <button
              disabled={isSubmitting || !photo}
              className="w-full rounded-2xl bg-[#EA0A2C] py-4 text-sm font-semibold text-white shadow-[0_10px_30px_-10px_rgba(234,10,44,0.5)] transition-all hover:bg-[#C80825] active:scale-[0.98] disabled:cursor-not-allowed disabled:bg-gray-300 disabled:shadow-none"
            >
              {isSubmitting ? "Mengunggah…" : "Kirim laporan"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return null;
}
