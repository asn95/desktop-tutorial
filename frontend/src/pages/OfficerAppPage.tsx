import { useState, useEffect } from "react";
import { apiClient } from "../lib/apiClient";
import { formatCurrency } from "../lib/format";
import type { Target } from "../types/target";

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
  const [paymentStatus, setPaymentStatus] = useState("Promise to Pay");
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
      alert("Officer profile not found. Please register your Telegram ID in the Admin Portal.");
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
      alert("Report submitted successfully!");
      // Back to list
      const res = await apiClient.get<Target[]>(`/officer/tasks/${telegramId}`);
      setTasks(res.data);
      setView("list");
      setSelectedTarget(null);
      setNotes("");
      setPhoto(null);
    } catch (err) {
      alert("Submission failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (view === "login") {
    return (
      <div className="min-h-screen bg-[#e9eff6] flex items-center justify-center p-6 font-sans">
        <div className="w-full max-w-[400px] bg-white rounded-2xl p-10 shadow-2xl">
          <div className="text-center mb-8">
            <div className="text-3xl font-black tracking-tighter mb-2">
              <span className="text-[#e11d48]">C</span>3MR FIELD
            </div>
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Operative Access</p>
          </div>
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-[11px] font-black uppercase text-slate-500">Telegram identity</label>
              <input 
                value={telegramId}
                onChange={(e) => setTelegramId(e.target.value)}
                placeholder="Enter your ID"
                className="w-full border border-slate-200 bg-slate-50 rounded-xl px-4 py-4 text-sm font-bold outline-none focus:border-black transition"
              />
            </div>
            <button 
              onClick={handleLogin}
              className="w-full bg-black text-white rounded-xl py-4 text-xs font-black uppercase tracking-widest shadow-xl active:scale-95 transition"
            >
              Verify Identity
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (view === "list") {
    return (
      <div className="min-h-screen bg-[#f8fafc] font-sans pb-10">
        <header className="bg-white border-b border-slate-200 px-6 py-5 sticky top-0 z-10 flex items-center justify-between">
          <div className="font-black tracking-tighter text-xl"><span className="text-[#e11d48]">C</span>3MR</div>
          <div className="text-[9px] font-black uppercase tracking-widest bg-black text-white px-3 py-1 rounded-full">Officer App</div>
        </header>
        
        <div className="p-6 space-y-6">
          <h2 className="text-2xl font-black text-slate-800">Assigned Tasks</h2>
          <div className="space-y-4">
            {tasks.length === 0 ? (
              <p className="text-slate-400 italic text-sm py-10 text-center">No assignments found.</p>
            ) : (
              tasks.map(task => (
                <div 
                  key={task.id}
                  onClick={() => { setSelectedTarget(task); setView("detail"); }}
                  className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm active:bg-slate-50 transition cursor-pointer"
                >
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">#{task.id.slice(0,6)}</span>
                    <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                      task.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {task.status}
                    </span>
                  </div>
                  <h3 className="font-bold text-slate-800 mb-1">{task.customerName}</h3>
                  <p className="text-xs text-slate-500 mb-4 line-clamp-1">{task.address}</p>
                  <div className="text-lg font-black text-red-600">{formatCurrency(task.amountDue)}</div>
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
      <div className="min-h-screen bg-white font-sans pb-10">
        <header className="px-6 py-5 flex items-center gap-4">
          <button onClick={() => setView("list")} className="text-slate-400 hover:text-black">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M15 19l-7-7 7-7" /></svg>
          </button>
          <div className="font-black uppercase text-[10px] tracking-widest text-slate-400">Task Detail</div>
        </header>

        <div className="px-6 space-y-8">
          <section>
            <h2 className="text-3xl font-black text-slate-800 mb-2 leading-tight">{selectedTask.customerName}</h2>
            <p className="text-sm font-medium text-slate-500 leading-relaxed">{selectedTask.address}</p>
            <div className="mt-6 inline-block bg-red-50 px-4 py-2 rounded-xl text-xl font-black text-red-600">
              {formatCurrency(selectedTask.amountDue)}
            </div>
          </section>

          <div className="h-[1px] bg-slate-100" />

          <form onSubmit={handleSubmitReport} className="space-y-8">
            <div className="space-y-3">
              <label className="text-[11px] font-black uppercase tracking-wider text-slate-400">Collection Status</label>
              <select 
                value={paymentStatus}
                onChange={(e) => setPaymentStatus(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-4 text-sm font-bold outline-none appearance-none"
              >
                <option>Promise to Pay</option>
                <option>Paid</option>
                <option>Refused</option>
                <option>Not Home</option>
                <option>Partial Payment</option>
              </select>
            </div>

            <div className="space-y-3">
              <label className="text-[11px] font-black uppercase tracking-wider text-slate-400">Visit Notes</label>
              <textarea 
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-4 text-sm font-bold outline-none"
                placeholder="Describe visit outcome..."
              />
            </div>

            <div className="space-y-3">
              <label className="text-[11px] font-black uppercase tracking-wider text-slate-400">Photo Evidence</label>
              <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-200 bg-slate-50 rounded-2xl cursor-pointer hover:bg-slate-100 transition">
                <div className="text-center">
                  <svg className="w-8 h-8 text-slate-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                  <p className="text-[10px] font-bold text-slate-500 uppercase">{photo ? photo.name : "Capture Photo Proof"}</p>
                </div>
                <input type="file" className="hidden" accept="image/*" capture="environment" onChange={(e) => setPhoto(e.target.files?.[0] || null)} />
              </label>
            </div>

            <button 
              disabled={isSubmitting || !photo}
              className="w-full bg-[#0f172a] text-white rounded-2xl py-5 text-sm font-black uppercase tracking-[0.2em] shadow-2xl active:scale-[0.98] transition disabled:opacity-30"
            >
              {isSubmitting ? "Uploading Data..." : "Submit Official Report"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return null;
}
