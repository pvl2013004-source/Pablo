import { useEffect, useRef, useState } from "react";
import "@/App.css";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Plus, Send, Trash2, Menu, X, BookOpen } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SUGGESTIONS = [
  {
    title: "Triángulo rectángulo",
    prompt: "Quiero calcular la hipotenusa de un triángulo con catetos de 3 y 4.",
  },
  {
    title: "Verbo en pretérito",
    prompt: "Necesito conjugar el verbo 'tener' en pretérito indefinido.",
  },
  {
    title: "Ecuación cuadrática",
    prompt: "Quiero resolver la ecuación x² - 5x + 6 = 0.",
  },
  {
    title: "Derivada de función",
    prompt: "Quiero hallar la derivada de f(x) = 3x² + 2x - 1.",
  },
];

function LoadingDots() {
  return (
    <div className="flex items-center gap-1 py-2" data-testid="loading-indicator">
      <span className="loading-dot"></span>
      <span className="loading-dot"></span>
      <span className="loading-dot"></span>
    </div>
  );
}

function TutorMessage({ content }) {
  // Split rendering into 3 sections by markdown headings (## Archivo de Datos / ## Paso Activo / ## Acción de Cierre)
  const sections = parseSections(content);

  return (
    <div className="mb-12 flex flex-col gap-4" data-testid="tutor-message">
      {sections.archivo && (
        <section
          className="border-l-2 pl-4 p-4 markdown-content"
          style={{ borderColor: "var(--text-primary)", background: "var(--surface)" }}
          data-testid="section-archivo-datos"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.25em]" style={{ color: "var(--text-secondary)" }}>
            01 — Archivo de Datos
          </span>
          <div className="mt-2">
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {sections.archivo}
            </ReactMarkdown>
          </div>
        </section>
      )}

      {sections.paso && (
        <section
          className="border-l-2 pl-4 p-4 markdown-content"
          style={{ borderColor: "var(--accent)", background: "rgba(0,85,255,0.04)" }}
          data-testid="section-paso-activo"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.25em]" style={{ color: "var(--accent)" }}>
            02 — Paso Activo
          </span>
          <div className="mt-2" style={{ color: "var(--accent)" }}>
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {sections.paso}
            </ReactMarkdown>
          </div>
        </section>
      )}

      {sections.cierre && (
        <section
          className="border-l-2 pl-4 p-4 markdown-content italic"
          style={{ borderColor: "var(--border)" }}
          data-testid="section-accion-cierre"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.25em] not-italic" style={{ color: "var(--text-secondary)" }}>
            03 — Acción de Cierre
          </span>
          <div className="mt-2 font-bold">
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {sections.cierre}
            </ReactMarkdown>
          </div>
        </section>
      )}

      {!sections.archivo && !sections.paso && !sections.cierre && (
        <div className="markdown-content p-4 border-l-2" style={{ borderColor: "var(--border)" }}>
          <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
            {content}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}

function parseSections(text) {
  const out = { archivo: "", paso: "", cierre: "" };
  if (!text) return out;
  // Match ## headings
  const regex = /##\s*(Archivo de Datos|Paso Activo|Acción de Cierre|Accion de Cierre)\s*\n([\s\S]*?)(?=\n##\s|$)/gi;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const key = match[1].toLowerCase();
    const body = match[2].trim();
    if (key.includes("archivo")) out.archivo = body;
    else if (key.includes("paso")) out.paso = body;
    else if (key.includes("cierre") || key.includes("acción") || key.includes("accion")) out.cierre = body;
  }
  return out;
}

function UserMessage({ content }) {
  return (
    <div className="mb-12 flex flex-col items-end" data-testid="user-message">
      <div
        className="p-4 max-w-[80%] font-body border"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        {content}
      </div>
    </div>
  );
}

function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const scrollRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => { fetchSessions(); }, []);

  useEffect(() => {
    if (activeSessionId) fetchMessages(activeSessionId);
    else setMessages([]);
  }, [activeSessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function fetchSessions() {
    try {
      const { data } = await axios.get(`${API}/chat/sessions`);
      setSessions(data);
    } catch (e) { console.error(e); }
  }

  async function fetchMessages(sid) {
    try {
      const { data } = await axios.get(`${API}/chat/sessions/${sid}/messages`);
      setMessages(data);
    } catch (e) { console.error(e); }
  }

  async function newSession() {
    try {
      const { data } = await axios.post(`${API}/chat/sessions`);
      setSessions((s) => [data, ...s]);
      setActiveSessionId(data.id);
      setMessages([]);
      setSidebarOpen(false);
      return data.id;
    } catch (e) { console.error(e); return null; }
  }

  async function deleteSession(id, e) {
    e.stopPropagation();
    try {
      await axios.delete(`${API}/chat/sessions/${id}`);
      setSessions((s) => s.filter((x) => x.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch (e) { console.error(e); }
  }

  async function sendMessage(textArg) {
    const text = (textArg ?? input).trim();
    if (!text || sending) return;
    let sid = activeSessionId;
    if (!sid) {
      sid = await newSession();
      if (!sid) return;
    }
    setInput("");
    setSending(true);
    // Optimistic user message
    const tempId = "tmp-" + Date.now();
    setMessages((m) => [...m, { id: tempId, session_id: sid, role: "user", content: text }]);
    try {
      const { data } = await axios.post(`${API}/chat/sessions/${sid}/message`, { content: text });
      setMessages((m) => [
        ...m.filter((x) => x.id !== tempId),
        data.user_message,
        data.assistant_message,
      ]);
      // Update session list
      setSessions((s) => {
        const others = s.filter((x) => x.id !== data.session.id);
        return [data.session, ...others];
      });
    } catch (e) {
      console.error(e);
      setMessages((m) => [
        ...m,
        { id: "err-" + Date.now(), session_id: sid, role: "assistant", content: "Error: no se pudo obtener respuesta del modelo." },
      ]);
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="App min-h-screen flex" style={{ background: "var(--bg)", color: "var(--text-primary)" }}>
      {/* Sidebar */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-30 w-72 border-r flex flex-col transition-transform ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        data-testid="sidebar"
      >
        <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2">
            <BookOpen size={18} strokeWidth={1.5} />
            <span className="font-heading font-black text-sm tracking-tight">TUTOR_MÉTODO</span>
          </div>
          <button
            className="md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="Cerrar"
            data-testid="close-sidebar-btn"
          >
            <X size={18} />
          </button>
        </div>

        <button
          onClick={newSession}
          className="m-4 flex items-center justify-center gap-2 p-3 font-mono uppercase text-[11px] tracking-[0.2em] transition-colors"
          style={{ background: "var(--text-primary)", color: "white" }}
          data-testid="new-session-button"
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0,0,0,0.8)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "var(--text-primary)")}
        >
          <Plus size={14} strokeWidth={2} /> Nueva sesión
        </button>

        <div className="flex-1 overflow-y-auto px-2 pb-4" data-testid="session-list">
          <div className="font-mono text-[10px] uppercase tracking-[0.25em] px-2 py-2" style={{ color: "var(--text-secondary)" }}>
            Historial
          </div>
          {sessions.length === 0 && (
            <div className="px-3 py-2 text-xs" style={{ color: "var(--text-secondary)" }}>
              Sin sesiones aún.
            </div>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => { setActiveSessionId(s.id); setSidebarOpen(false); }}
              className="group flex items-center justify-between gap-2 px-3 py-2.5 text-sm cursor-pointer border-l-2 transition-colors"
              style={{
                borderColor: activeSessionId === s.id ? "var(--text-primary)" : "transparent",
                background: activeSessionId === s.id ? "var(--surface-hover)" : "transparent",
                color: activeSessionId === s.id ? "var(--text-primary)" : "var(--text-secondary)",
              }}
              data-testid={`session-item-${s.id}`}
            >
              <span className="truncate flex-1">{s.title}</span>
              <button
                onClick={(e) => deleteSession(s.id, e)}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label="Borrar sesión"
                data-testid={`delete-session-${s.id}`}
              >
                <Trash2 size={14} strokeWidth={1.5} />
              </button>
            </div>
          ))}
        </div>

        <div className="p-4 border-t font-mono text-[10px] uppercase tracking-[0.2em]" style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}>
          v1.0 — Método activo
        </div>
      </aside>

      {/* Main area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top bar (mobile) */}
        <header className="md:hidden flex items-center justify-between p-4 border-b" style={{ borderColor: "var(--border)" }}>
          <button onClick={() => setSidebarOpen(true)} aria-label="Abrir menú" data-testid="open-sidebar-btn">
            <Menu size={20} />
          </button>
          <span className="font-heading font-black text-sm">TUTOR_MÉTODO</span>
          <div style={{ width: 20 }} />
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto pb-40">
          <div className="max-w-3xl mx-auto w-full px-4 sm:px-8 pt-12">
            {messages.length === 0 ? (
              <EmptyState onPick={(p) => sendMessage(p)} />
            ) : (
              <>
                {messages.map((m) =>
                  m.role === "user" ? (
                    <UserMessage key={m.id} content={m.content} />
                  ) : (
                    <TutorMessage key={m.id} content={m.content} />
                  )
                )}
                {sending && <LoadingDots />}
              </>
            )}
          </div>
        </div>

        {/* Input bar */}
        <div
          className="fixed bottom-0 right-0 left-0 md:left-72 border-t p-4 sm:p-6"
          style={{ background: "rgba(255,255,255,0.92)", backdropFilter: "blur(12px)", borderColor: "var(--border)" }}
          data-testid="input-bar"
        >
          <div className="max-w-3xl mx-auto flex gap-3 items-stretch">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Plantea tu problema o duda académica…"
              rows={1}
              className="flex-1 p-4 text-base font-body outline-none resize-none border transition-colors"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
                color: "var(--text-primary)",
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = "var(--text-primary)")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
              data-testid="prompt-input"
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || sending}
              className="px-6 sm:px-8 font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: "var(--accent)", color: "white" }}
              onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = "var(--accent-hover)"; }}
              onMouseLeave={(e) => (e.currentTarget.style.background = "var(--accent)")}
              data-testid="send-button"
            >
              <Send size={16} strokeWidth={2} />
              <span className="hidden sm:inline font-mono uppercase text-xs tracking-[0.2em]">Enviar</span>
            </button>
          </div>
          <div className="max-w-3xl mx-auto mt-2 font-mono text-[10px] uppercase tracking-[0.2em]" style={{ color: "var(--text-secondary)" }}>
            Enter para enviar · Shift + Enter para nueva línea
          </div>
        </div>
      </main>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
          data-testid="sidebar-overlay"
        />
      )}
    </div>
  );
}

function EmptyState({ onPick }) {
  return (
    <div className="flex flex-col items-start max-w-2xl mx-auto pt-8 pb-12" data-testid="empty-state">
      <span className="font-mono text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--text-secondary)" }}>
        Sistema · Método activo · Sin respuestas finales
      </span>
      <h1 className="font-heading text-4xl sm:text-5xl font-black tracking-tight mt-4 leading-[1.05]">
        Tutor<br/>Metodológico.
      </h1>
      <p className="mt-6 text-base leading-relaxed" style={{ color: "var(--text-secondary)" }}>
        No te entrego el resultado. Te entrego los datos, una sola acción y una pregunta.
        Aprendes haciendo el siguiente paso.
      </p>

      <div className="mt-12 w-full">
        <span className="font-mono text-[10px] uppercase tracking-[0.25em]" style={{ color: "var(--text-secondary)" }}>
          Inicia con un ejemplo
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              onClick={() => onPick(s.prompt)}
              className="text-left p-4 border transition-all bg-white"
              style={{ borderColor: "var(--border)" }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--text-primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
              data-testid={`suggestion-${i}`}
            >
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] mb-2" style={{ color: "var(--text-secondary)" }}>
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="font-heading font-bold text-base leading-tight">{s.title}</div>
              <div className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>
                {s.prompt}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
