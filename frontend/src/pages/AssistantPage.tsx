import { FormEvent, useEffect, useRef, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { apiClient } from "../lib/apiClient";

interface Msg {
  role: "user" | "assistant";
  text: string;
}

const SUGGESTIONS = [
  "Berapa collection rate kita?",
  "Target mana yang sudah jatuh tempo?",
  "Siapa petugas dengan kinerja terbaik?",
  "Buatkan laporan harian",
];

// Riwayat chat disimpan di localStorage agar tidak hilang saat pindah halaman.
// Dibersihkan otomatis saat logout (lihat AuthContext) dan dibatasi agar tidak menumpuk.
export const ASSISTANT_CHAT_KEY = "c3mr:assistant-chat";
const MAX_STORED_MESSAGES = 100;

function readStoredMessages(): Msg[] {
  try {
    const raw = localStorage.getItem(ASSISTANT_CHAT_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function AssistantPage() {
  const [messages, setMessages] = useState<Msg[]>(() => readStoredMessages());
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Persist riwayat ke localStorage setiap kali berubah (dibatasi MAX_STORED_MESSAGES).
  useEffect(() => {
    try {
      if (messages.length === 0) {
        localStorage.removeItem(ASSISTANT_CHAT_KEY);
      } else {
        localStorage.setItem(ASSISTANT_CHAT_KEY, JSON.stringify(messages.slice(-MAX_STORED_MESSAGES)));
      }
    } catch {
      /* localStorage penuh / tidak tersedia — abaikan, riwayat tetap di memori */
    }
  }, [messages]);

  const clearChat = () => {
    setMessages([]);
    setInput("");
  };

  async function send(q: string) {
    const question = q.trim();
    if (!question || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", text: question }]);
    setLoading(true);
    try {
      const res = await apiClient.post("/agent/ask", { question }, { timeout: 90_000 });
      setMessages(prev => [...prev, { role: "assistant", text: res.data.answer || "—" }]);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Tidak bisa menghubungi asisten. Silakan coba lagi.";
      setMessages(prev => [...prev, { role: "assistant", text: msg }]);
    } finally {
      setLoading(false);
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    send(input);
  };

  return (
    <AppShell>
      <div className="mx-auto flex max-w-3xl flex-col">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">Asisten AI</h1>
            <p className="mt-1 text-sm text-gray-500">
              Tanya soal penagihan, target, petugas, atau laporan pakai bahasa sehari-hari.
            </p>
          </div>
          {messages.length > 0 && (
            <button
              type="button"
              onClick={clearChat}
              className="shrink-0 rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium text-gray-500 transition-colors hover:border-[#EA0A2C]/40 hover:bg-red-50 hover:text-[#EA0A2C]"
            >
              Bersihkan riwayat
            </button>
          )}
        </div>

        <div className="flex h-[68vh] flex-col overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
          {/* Messages */}
          <div className="flex-1 space-y-4 overflow-y-auto p-5 sm:p-6">
            {messages.length === 0 && !loading ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#EA0A2C]/10 text-[#EA0A2C]">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
                    <path d="M12 3l1.7 4.3L18 9l-4.3 1.7L12 15l-1.7-4.3L6 9l4.3-1.7z" />
                    <path d="M18.5 14.5l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z" />
                  </svg>
                </span>
                <p className="mt-4 text-sm font-semibold text-gray-900">Ada yang bisa saya bantu?</p>
                <p className="mt-1 text-xs text-gray-400">Ditenagai Claude (Anthropic) · membaca data C3MR langsung</p>
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map(s => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:border-[#EA0A2C]/40 hover:bg-red-50 hover:text-[#EA0A2C]"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                      m.role === "user" ? "bg-[#EA0A2C] text-white" : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {m.text}
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-2xl bg-gray-100 px-4 py-3.5">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <form onSubmit={onSubmit} className="border-t border-gray-100 p-3 sm:p-4">
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Tanya apa saja soal operasional Anda…"
                disabled={loading}
                className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 placeholder-gray-400 outline-none transition focus:border-[#EA0A2C] focus:ring-2 focus:ring-[#EA0A2C]/20 disabled:bg-gray-50"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="rounded-xl bg-[#EA0A2C] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#C80825] disabled:cursor-not-allowed disabled:bg-gray-300"
              >
                Kirim
              </button>
            </div>
          </form>
        </div>
      </div>
    </AppShell>
  );
}
