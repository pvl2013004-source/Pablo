import { useEffect, useRef, useState } from "react";
import "@/App.css";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Plus, Send, Trash2, Menu, X } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const LOGO_SRC = "/syvren-logo.jpeg";

const SUGGESTIONS = [
  { title: "Triángulo rectángulo", prompt: "Quiero calcular la hipotenusa de un triángulo con catetos de 3 y 4." },
  { title: "Verbo en pretérito", prompt: "Necesito conjugar el verbo 'tener' en pretérito indefinido." },
  { title: "Ecuación cuadrática", prompt: "Quiero resolver la ecuación x² - 5x + 6 = 0." },
  { title: "Derivada de función", prompt: "Quiero hallar la derivada de f(x) = 3x² + 2x - 1." },
];

function Brand({ size = "md" }) {
  const dims = size === "lg" ? { img: 64, title: "text-2xl", sub: "text-[10px]" } : { img: 38, title: "text-base", sub: "text-[9px]" };
  return (
    <div className="flex items-center gap-3" data-testid="brand">
      <img
        src={LOGO_SRC}
        alt="Syvren"
        width={dims.img}
        height={dims.img}
        className="object-contain"
        style={{ filter: "drop-shadow(0 0 12px rgba(59,130,246,0.35))" }}
      />
      <div className="flex flex-col leading-none">
        <span
          className={`font-heading font-black tracking-[0.18em] ${dims.title}`}
          style={{
            background: "linear-gradient(135deg, #60A5FA 0%, #22D3EE 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          SYVREN
        </span>
        <span className={`font-mono uppercase tracking-[0.3em] mt-1 ${dims.sub}`} style={{ color: "var(--text-muted)" }}>
          Since 2026
        </span>
      </div>
    </div>
  );
}

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
  const sections = parseSections(content);

  return (
    <div className="mb-12 flex flex-col gap-4" data-testid="tutor-message">
      {sections.archivo && (
        <section
          className="border-l-2 pl-4 p-4 markdown-content"
          style={{ borderColor: "var(--accent-cyan)", background: "var(--surface)" }}
          data-testid="section-archivo-datos"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.25em]" style={{ color: "var(--accent-cyan)" }}>
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
          style={{
            borderColor: "var(--accent)",
            background: "linear-gradient(90deg, rgba(59,130,246,0.12), rgba(59,130,246,0.02))",
          }}
          data-testid="section-paso-activo"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.25em]" style={{ color: "var(--accent-hover)" }}>
            02 — Paso Activo
          </span>
          <div className="mt-2" style={{ color: "#DBEAFE" }}>
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
              {sections.paso}
            </ReactMarkdown>
          </div>
        </section>
      )}

      {sections.cierre && (
        <section
          className="border-l-2 pl-4 p-4 markdown-content italic"
          style={{ borderColor: "var(--border-strong)" }}
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
        <div className="markdown-content p-4 border-l-2" style={{ borderColor: "var(--border-strong)" }}>
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
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-strong)",
          color: "var(--text-primary)",
        }}
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
    const tempId = "tmp-" + Date.now();
    setMessages((m) => [...m, { id: tempId, session_id: sid, role: "user", content: text }]);
    try {
      const { data } = await axios.post(`${API}/chat/sessions/${sid}/message`, { content: text });
      setMessages((m) => {
        const map = new Map(m.filter((x) => x.id !== tempId).map((x) => [x.id, x]));
        map.set(data.user_message.id, data.user_message);
        map.set(data.assistant_message.id, data.assistant_message);
        return Array.from(map.values());
      });
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
    <div
      className="App min-h-screen flex"
      style={{
        background:
          "radial-gradient(ellipse at top left, rgba(30,64,175,0.15), transparent 50%), radial-gradient(ellipse at bottom right, rgba(34,211,238,0.06), transparent 50%), var(--bg)",
        color: "var(--text-primary)",
      }}
    >
      {/* Sidebar */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-30 w-72 border-r flex flex-col transition-transform ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
        style={{ background: "var(--bg-deep)", borderColor: "var(--border)" }}
        data-testid="sidebar"
      >
        <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
          <Brand size="md" />
          <button
            className="md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="Cerrar"
            data-testid="close-sidebar-btn"
            style={{ color: "var(--text-secondary)" }}
          >
            <X size={18} />
          </button>
        </div>

        <button
          onClick={newSession}
          className="m-4 flex items-center justify-center gap-2 p-3 font-mono uppercase text-[11px] tracking-[0.2em] transition-all"
          style={{
            background: "linear-gradient(135deg, var(--accent) 0%, var(--accent-cyan) 100%)",
            color: "#031024",
            fontWeight: 700,
            boxShadow: "0 0 0 1px rgba(59,130,246,0.3), 0 4px 24px -8px rgba(59,130,246,0.5)",
          }}
          data-testid="new-session-button"
          onMouseEnter={(e) => (e.currentTarget.style.filter = "brightness(1.1)")}
          onMouseLeave={(e) => (e.currentTarget.style.filter = "brightness(1)")}
        >
          <Plus size={14} strokeWidth={2.5} /> Nueva sesión
        </button>

        <div className="flex-1 overflow-y-auto px-2 pb-4" data-testid="session-list">
          <div className="font-mono text-[10px] uppercase tracking-[0.25em] px-2 py-2" style={{ color: "var(--text-muted)" }}>
            Historial
          </div>
          {sessions.length === 0 && (
            <div className="px-3 py-2 text-xs" style={{ color: "var(--text-muted)" }}>
              Sin sesiones aún.
            </div>
          )}
          {sessions.map((s) => {
            const active = activeSessionId === s.id;
            return (
              <div
                key={s.id}
                onClick={() => { setActiveSessionId(s.id); setSidebarOpen(false); }}
                className="group flex items-center justify-between gap-2 px-3 py-2.5 text-sm cursor-pointer border-l-2 transition-all"
                style={{
                  borderColor: active ? "var(--accent)" : "transparent",
                  background: active ? "var(--surface-hover)" : "transparent",
                  color: active ? "var(--text-primary)" : "var(--text-secondary)",
                }}
                onMouseEnter={(e) => {
                  if (!active) {
                    e.currentTarget.style.background = "var(--surface)";
                    e.currentTarget.style.color = "var(--text-primary)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    e.currentTarget.style.background = "transparent";
                    e.currentTarget.style.color = "var(--text-secondary)";
                  }
                }}
                data-testid={`session-item-${s.id}`}
              >
                <span className="truncate flex-1">{s.title}</span>
                <button
                  onClick={(e) => deleteSession(s.id, e)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                  aria-label="Borrar sesión"
                  data-testid={`delete-session-${s.id}`}
                  style={{ color: "var(--text-muted)" }}
                >
                  <Trash2 size={14} strokeWidth={1.5} />
                </button>
              </div>
            );
          })}
        </div>

        <div className="p-4 border-t font-mono text-[10px] uppercase tracking-[0.2em]" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
          v1.0 — Método activo
        </div>
      </aside>

      {/* Main area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top bar (mobile) */}
        <header className="md:hidden flex items-center justify-between p-4 border-b" style={{ borderColor: "var(--border)", background: "var(--bg-deep)" }}>
          <button onClick={() => setSidebarOpen(true)} aria-label="Abrir menú" data-testid="open-sidebar-btn" style={{ color: "var(--text-primary)" }}>
            <Menu size={20} />
          </button>
          <Brand size="md" />
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
          style={{
            background: "rgba(5,11,31,0.85)",
            backdropFilter: "blur(14px)",
            borderColor: "var(--border)",
          }}
          data-testid="input-bar"
        >
          <div className="max-w-3xl mx-auto flex gap-3 items-stretch">
            <textarea
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
              onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
              data-testid="prompt-input"
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || sending}
              className="px-6 sm:px-8 font-bold flex items-center justify-center gap-2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                background: "linear-gradient(135deg, var(--accent) 0%, var(--accent-cyan) 100%)",
                color: "#031024",
                boxShadow: "0 0 0 1px rgba(59,130,246,0.3), 0 4px 24px -8px rgba(59,130,246,0.6)",
              }}
              onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.filter = "brightness(1.1)"; }}
              onMouseLeave={(e) => (e.currentTarget.style.filter = "brightness(1)")}
              data-testid="send-button"
            >
              <Send size={16} strokeWidth={2.5} />
              <span className="hidden sm:inline font-mono uppercase text-xs tracking-[0.2em]">Enviar</span>
            </button>
          </div>
          <div className="max-w-3xl mx-auto mt-2 font-mono text-[10px] uppercase tracking-[0.2em]" style={{ color: "var(--text-muted)" }}>
            Enter para enviar · Shift + Enter para nueva línea
          </div>
        </div>
      </main>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 md:hidden"
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
      <div className="brand-glow w-full flex flex-col items-start py-8 -my-8">
        <Brand size="lg" />
        <span className="font-mono text-[10px] uppercase tracking-[0.3em] mt-8" style={{ color: "var(--text-muted)" }}>
          Sistema · Método activo · Sin respuestas finales
        </span>
        <h1
          className="font-heading text-4xl sm:text-5xl font-black tracking-tight mt-4 leading-[1.05]"
          style={{ color: "var(--text-primary)" }}
        >
          Tutor<br/>
          <span
            style={{
              background: "linear-gradient(135deg, #60A5FA 0%, #22D3EE 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Metodológico.
          </span>
        </h1>
        <p className="mt-6 text-base leading-relaxed max-w-xl" style={{ color: "var(--text-secondary)" }}>
          No te entrego el resultado. Te entrego los datos, una sola acción y una pregunta.
          Aprendes haciendo el siguiente paso.
        </p>
      </div>

      <div className="mt-12 w-full">
        <span className="font-mono text-[10px] uppercase tracking-[0.25em]" style={{ color: "var(--text-muted)" }}>
          Inicia con un ejemplo
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              onClick={() => onPick(s.prompt)}
              className="text-left p-4 border transition-all"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
                color: "var(--text-primary)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--accent)";
                e.currentTarget.style.background = "var(--surface-hover)";
                e.currentTarget.style.boxShadow = "0 0 24px -8px rgba(59,130,246,0.4)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.background = "var(--surface)";
                e.currentTarget.style.boxShadow = "none";
              }}
              data-testid={`suggestion-${i}`}
            >
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] mb-2" style={{ color: "var(--accent-cyan)" }}>
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
