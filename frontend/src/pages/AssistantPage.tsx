import { FormEvent, useEffect, useRef, useState } from "react";
import { AppShell } from "../components/layout/AppShell";
import { apiClient } from "../lib/apiClient";

interface Msg {
  role: "user" | "assistant";
  text: string;
}

const SUGGESTIONS = [
  "What's our collection rate?",
  "Which targets are overdue?",
  "Who's the top performing officer?",
  "Generate a daily report",
];

export function AssistantPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

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
      const msg = err.response?.data?.detail || "Couldn't reach the assistant. Please try again.";
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
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">AI Assistant</h1>
          <p className="mt-1 text-sm text-gray-500">
            Ask about collections, targets, officers, or reports in natural language.
          </p>
        </div>

        <div className="flex h-[68vh] flex-col overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-[0_2px_20px_-8px_rgba(16,24,40,0.12)]">
          {/* Messages */}
          <div className="flex-1 space-y-4 overflow-y-auto p-5 sm:p-6">
            {messages.length === 0 && !loading ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#E81E28]/10 text-[#E81E28]">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
                    <path d="M12 3l1.7 4.3L18 9l-4.3 1.7L12 15l-1.7-4.3L6 9l4.3-1.7z" />
                    <path d="M18.5 14.5l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z" />
                  </svg>
                </span>
                <p className="mt-4 text-sm font-semibold text-gray-900">How can I help?</p>
                <p className="mt-1 text-xs text-gray-400">Powered by Gemini · queries live C3MR data</p>
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map(s => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:border-[#E81E28]/40 hover:bg-red-50 hover:text-[#E81E28]"
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
                      m.role === "user" ? "bg-[#E81E28] text-white" : "bg-gray-100 text-gray-800"
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
                placeholder="Ask anything about your operations…"
                disabled={loading}
                className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 placeholder-gray-400 outline-none transition focus:border-[#E81E28] focus:ring-2 focus:ring-[#E81E28]/20 disabled:bg-gray-50"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="rounded-xl bg-[#E81E28] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#c8161f] disabled:cursor-not-allowed disabled:bg-gray-300"
              >
                Send
              </button>
            </div>
          </form>
        </div>
      </div>
    </AppShell>
  );
}
