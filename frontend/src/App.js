import { useEffect, useRef, useState } from "react";
import "@/App.css";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Plus, Send, Trash2, Menu, X, Globe, Check } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const LOGO_SRC = "/syvren-logo.jpeg";

const LANGS = [
  { code: "es", label: "Español", short: "ES" },
  { code: "en", label: "English", short: "EN" },
  { code: "fr", label: "Français", short: "FR" },
  { code: "pt", label: "Português", short: "PT" },
];

const I18N = {
  es: {
    new_session: "Nueva sesión",
    history: "Historial",
    no_sessions: "Sin sesiones aún.",
    placeholder: "Plantea tu problema o duda académica…",
    send: "Enviar",
    hint: "Enter para enviar · Shift + Enter para nueva línea",
    method_label: "v1.0 — Método activo",
    hero_chip: "Sistema · Método activo · Sin respuestas finales",
    hero_title_1: "Tutor",
    hero_title_2: "Metodológico.",
    hero_desc: "No te entrego el resultado. Te entrego los datos, una sola acción y una pregunta. Aprendes haciendo el siguiente paso.",
    start_with: "Inicia con un ejemplo",
    error_msg: "Error: no se pudo obtener respuesta del modelo.",
    section_archivo: "Archivo de Datos",
    section_paso: "Paso Activo",
    section_cierre: "Acción de Cierre",
    suggestions: [
      { title: "Triángulo rectángulo", prompt: "Quiero calcular la hipotenusa de un triángulo con catetos de 3 y 4." },
      { title: "Multiplicación", prompt: "Quiero calcular 23 × 47 paso a paso." },
      { title: "Ecuación cuadrática", prompt: "Quiero resolver la ecuación x² - 5x + 6 = 0." },
      { title: "Derivada de función", prompt: "Quiero hallar la derivada de f(x) = 3x² + 2x - 1." },
    ],
  },
  en: {
    new_session: "New session",
    history: "History",
    no_sessions: "No sessions yet.",
    placeholder: "Pose your problem or academic question…",
    send: "Send",
    hint: "Enter to send · Shift + Enter for newline",
    method_label: "v1.0 — Active method",
    hero_chip: "System · Active method · No final answers",
    hero_title_1: "Methodological",
    hero_title_2: "Tutor.",
    hero_desc: "I won't hand you the result. I give you the data, one single action and one question. You learn by taking the next step.",
    start_with: "Start with an example",
    error_msg: "Error: could not get a response from the model.",
    section_archivo: "Data File",
    section_paso: "Active Step",
    section_cierre: "Closing Action",
    suggestions: [
      { title: "Right triangle", prompt: "I want to calculate the hypotenuse of a triangle with legs 3 and 4." },
      { title: "Multiplication", prompt: "I want to compute 23 × 47 step by step." },
      { title: "Quadratic equation", prompt: "I want to solve the equation x² - 5x + 6 = 0." },
      { title: "Derivative", prompt: "I want to find the derivative of f(x) = 3x² + 2x - 1." },
    ],
  },
  fr: {
    new_session: "Nouvelle session",
    history: "Historique",
    no_sessions: "Aucune session encore.",
    placeholder: "Pose ton problème ou ta question académique…",
    send: "Envoyer",
    hint: "Entrée pour envoyer · Maj + Entrée pour nouvelle ligne",
    method_label: "v1.0 — Méthode active",
    hero_chip: "Système · Méthode active · Sans réponses finales",
    hero_title_1: "Tuteur",
    hero_title_2: "Méthodologique.",
    hero_desc: "Je ne te donne pas le résultat. Je te donne les données, une seule action et une question. Tu apprends en faisant le pas suivant.",
    start_with: "Commence par un exemple",
    error_msg: "Erreur : impossible d'obtenir une réponse du modèle.",
    section_archivo: "Fichier de Données",
    section_paso: "Étape Active",
    section_cierre: "Action de Clôture",
    suggestions: [
      { title: "Triangle rectangle", prompt: "Je veux calculer l'hypoténuse d'un triangle avec des côtés 3 et 4." },
      { title: "Multiplication", prompt: "Je veux calculer 23 × 47 étape par étape." },
      { title: "Équation quadratique", prompt: "Je veux résoudre l'équation x² - 5x + 6 = 0." },
      { title: "Dérivée", prompt: "Je veux trouver la dérivée de f(x) = 3x² + 2x - 1." },
    ],
  },
  pt: {
    new_session: "Nova sessão",
    history: "Histórico",
    no_sessions: "Nenhuma sessão ainda.",
    placeholder: "Coloque seu problema ou dúvida acadêmica…",
    send: "Enviar",
    hint: "Enter para enviar · Shift + Enter para nova linha",
    method_label: "v1.0 — Método ativo",
    hero_chip: "Sistema · Método ativo · Sem respostas finais",
    hero_title_1: "Tutor",
    hero_title_2: "Metodológico.",
    hero_desc: "Não te entrego o resultado. Te entrego os dados, uma única ação e uma pergunta. Você aprende dando o próximo passo.",
    start_with: "Comece com um exemplo",
    error_msg: "Erro: não foi possível obter resposta do modelo.",
    section_archivo: "Arquivo de Dados",
    section_paso: "Passo Ativo",
    section_cierre: "Ação de Encerramento",
    suggestions: [
      { title: "Triângulo retângulo", prompt: "Quero calcular a hipotenusa de um triângulo com catetos de 3 e 4." },
      { title: "Multiplicação", prompt: "Quero calcular 23 × 47 passo a passo." },
      { title: "Equação quadrática", prompt: "Quero resolver a equação x² - 5x + 6 = 0." },
      { title: "Derivada", prompt: "Quero achar a derivada de f(x) = 3x² + 2x - 1." },
    ],
  },
};

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

function LangSwitcher({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    function onDocClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);
  const current = LANGS.find((l) => l.code === value) || LANGS[0];
  return (
    <div ref={ref} className="relative" data-testid="lang-switcher">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono uppercase tracking-[0.15em] border transition-all"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          color: "var(--text-primary)",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
        onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
        data-testid="lang-button"
        aria-label="Change language"
      >
        <Globe size={12} strokeWidth={2} />
        <span>{current.short}</span>
      </button>
      {open && (
        <div
          className="absolute right-0 mt-2 z-40 min-w-[140px] border shadow-xl"
          style={{ background: "var(--bg-deep)", borderColor: "var(--border-strong)" }}
          data-testid="lang-menu"
        >
          {LANGS.map((l) => {
            const active = l.code === value;
            return (
              <button
                key={l.code}
                onClick={() => { onChange(l.code); setOpen(false); }}
                className="w-full flex items-center justify-between gap-3 px-3 py-2 text-xs font-mono uppercase tracking-[0.15em] transition-colors"
                style={{
                  color: active ? "var(--accent-cyan)" : "var(--text-secondary)",
                  background: active ? "var(--surface-hover)" : "transparent",
                }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "var(--surface)"; }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
                data-testid={`lang-option-${l.code}`}
              >
                <span>{l.short} · {l.label}</span>
                {active && <Check size={12} strokeWidth={2.5} />}
              </button>
            );
          })}
        </div>
      )}
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

function TutorMessage({ content, t }) {
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
            01 — {t.section_archivo}
          </span>
          <div className="mt-2">
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{sections.archivo}</ReactMarkdown>
          </div>
        </section>
      )}
      {sections.paso && (
        <section
          className="border-l-2 pl-4 p-4 markdown-content"
          style={{ borderColor: "var(--accent)", background: "linear-gradient(90deg, rgba(59,130,246,0.12), rgba(59,130,246,0.02))" }}
          data-testid="section-paso-activo"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.25em]" style={{ color: "var(--accent-hover)" }}>
            02 — {t.section_paso}
          </span>
          <div className="mt-2" style={{ color: "#DBEAFE" }}>
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{sections.paso}</ReactMarkdown>
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
            03 — {t.section_cierre}
          </span>
          <div className="mt-2 font-bold">
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{sections.cierre}</ReactMarkdown>
          </div>
        </section>
      )}
      {!sections.archivo && !sections.paso && !sections.cierre && (
        <div className="markdown-content p-4 border-l-2" style={{ borderColor: "var(--border-strong)" }}>
          <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

// Section keywords across languages
const SECTION_MAP = {
  archivo: ["archivo de datos", "data file", "fichier de données", "fichier de donnees", "arquivo de dados"],
  paso: ["paso activo", "active step", "étape active", "etape active", "passo ativo"],
  cierre: ["acción de cierre", "accion de cierre", "closing action", "action de clôture", "action de cloture", "ação de encerramento", "acao de encerramento"],
};

function parseSections(text) {
  const out = { archivo: "", paso: "", cierre: "" };
  if (!text) return out;
  const regex = /##\s*([^\n]+?)\s*\n([\s\S]*?)(?=\n##\s|$)/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const heading = match[1].toLowerCase().trim();
    const body = match[2].trim();
    if (SECTION_MAP.archivo.some((k) => heading.includes(k))) out.archivo = body;
    else if (SECTION_MAP.paso.some((k) => heading.includes(k))) out.paso = body;
    else if (SECTION_MAP.cierre.some((k) => heading.includes(k))) out.cierre = body;
  }
  return out;
}

function UserMessage({ content }) {
  return (
    <div className="mb-12 flex flex-col items-end" data-testid="user-message">
      <div
        className="p-4 max-w-[80%] font-body border"
        style={{ background: "var(--surface)", borderColor: "var(--border-strong)", color: "var(--text-primary)" }}
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
  const [lang, setLang] = useState(() => localStorage.getItem("syvren_lang") || "es");
  const scrollRef = useRef(null);
  const t = I18N[lang] || I18N.es;

  useEffect(() => { fetchSessions(); }, []);
  useEffect(() => { localStorage.setItem("syvren_lang", lang); }, [lang]);

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
      const { data } = await axios.post(`${API}/chat/sessions/${sid}/message`, { content: text, language: lang });
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
        { id: "err-" + Date.now(), session_id: sid, role: "assistant", content: t.error_msg },
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
            aria-label="Close"
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
          <Plus size={14} strokeWidth={2.5} /> {t.new_session}
        </button>

        <div className="flex-1 overflow-y-auto px-2 pb-4" data-testid="session-list">
          <div className="font-mono text-[10px] uppercase tracking-[0.25em] px-2 py-2" style={{ color: "var(--text-muted)" }}>
            {t.history}
          </div>
          {sessions.length === 0 && (
            <div className="px-3 py-2 text-xs" style={{ color: "var(--text-muted)" }}>{t.no_sessions}</div>
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
                  if (!active) { e.currentTarget.style.background = "var(--surface)"; e.currentTarget.style.color = "var(--text-primary)"; }
                }}
                onMouseLeave={(e) => {
                  if (!active) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--text-secondary)"; }
                }}
                data-testid={`session-item-${s.id}`}
              >
                <span className="truncate flex-1">{s.title}</span>
                <button
                  onClick={(e) => deleteSession(s.id, e)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                  aria-label="Delete"
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
          {t.method_label}
        </div>
      </aside>

      {/* Main area */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        {/* Top bar (desktop) - lang switcher in top right */}
        <div className="hidden md:flex absolute top-4 right-6 z-20" data-testid="top-bar-desktop">
          <LangSwitcher value={lang} onChange={setLang} />
        </div>

        {/* Top bar (mobile) */}
        <header className="md:hidden flex items-center justify-between p-4 border-b" style={{ borderColor: "var(--border)", background: "var(--bg-deep)" }}>
          <button onClick={() => setSidebarOpen(true)} aria-label="Open menu" data-testid="open-sidebar-btn" style={{ color: "var(--text-primary)" }}>
            <Menu size={20} />
          </button>
          <Brand size="md" />
          <LangSwitcher value={lang} onChange={setLang} />
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto pb-40">
          <div className="max-w-3xl mx-auto w-full px-4 sm:px-8 pt-12">
            {messages.length === 0 ? (
              <EmptyState t={t} onPick={(p) => sendMessage(p)} />
            ) : (
              <>
                {messages.map((m) =>
                  m.role === "user" ? (
                    <UserMessage key={m.id} content={m.content} />
                  ) : (
                    <TutorMessage key={m.id} content={m.content} t={t} />
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
          style={{ background: "rgba(5,11,31,0.85)", backdropFilter: "blur(14px)", borderColor: "var(--border)" }}
          data-testid="input-bar"
        >
          <div className="max-w-3xl mx-auto flex gap-3 items-stretch">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={t.placeholder}
              rows={1}
              className="flex-1 p-4 text-base font-body outline-none resize-none border transition-colors"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text-primary)" }}
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
              <span className="hidden sm:inline font-mono uppercase text-xs tracking-[0.2em]">{t.send}</span>
            </button>
          </div>
          <div className="max-w-3xl mx-auto mt-2 font-mono text-[10px] uppercase tracking-[0.2em]" style={{ color: "var(--text-muted)" }}>
            {t.hint}
          </div>
        </div>
      </main>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 z-20 md:hidden" onClick={() => setSidebarOpen(false)} data-testid="sidebar-overlay" />
      )}
    </div>
  );
}

function EmptyState({ t, onPick }) {
  return (
    <div className="flex flex-col items-start max-w-2xl mx-auto pt-8 pb-12" data-testid="empty-state">
      <div className="brand-glow w-full flex flex-col items-start py-8 -my-8">
        <Brand size="lg" />
        <span className="font-mono text-[10px] uppercase tracking-[0.3em] mt-8" style={{ color: "var(--text-muted)" }}>
          {t.hero_chip}
        </span>
        <h1 className="font-heading text-4xl sm:text-5xl font-black tracking-tight mt-4 leading-[1.05]" style={{ color: "var(--text-primary)" }}>
          {t.hero_title_1}<br/>
          <span style={{ background: "linear-gradient(135deg, #60A5FA 0%, #22D3EE 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            {t.hero_title_2}
          </span>
        </h1>
        <p className="mt-6 text-base leading-relaxed max-w-xl" style={{ color: "var(--text-secondary)" }}>
          {t.hero_desc}
        </p>
      </div>

      <div className="mt-12 w-full">
        <span className="font-mono text-[10px] uppercase tracking-[0.25em]" style={{ color: "var(--text-muted)" }}>
          {t.start_with}
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
          {t.suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onPick(s.prompt)}
              className="text-left p-4 border transition-all"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text-primary)" }}
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
              <div className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>{s.prompt}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
