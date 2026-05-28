# SYVREN — Tutor Metodológico Minimalista (Production)

## Problema
Tutor IA con protocolo estricto: nunca da el resultado final, guía con datos + 1 paso + 1 pregunta.

## Arquitectura
- Frontend: React 19 + Tailwind + react-markdown + KaTeX + lucide-react
- Backend: FastAPI + Motor (MongoDB) + litellm (proxy Emergent Universal Key) + pypdf + httpx
- Auth: Emergent-managed Google OAuth (sin emergentintegrations en runtime)
- LLM: Claude Haiku 4.5 vía litellm directo → `https://integrations.emergentagent.com/llm`
- Hosting: Vercel (frontend) + Render/Vercel (backend) + MongoDB Atlas

## Implementado
- Chat con protocolo de 3 secciones (Archivo de Datos / Paso Activo / Acción de Cierre)
- 4 idiomas (ES/EN/FR/PT) con selector
- Descomposición automática de aritmética
- Adjuntos imagen (JPG/PNG/WEBP, 5MB) con vision
- Adjuntos PDF (10MB) con extracción de texto (cap 12000 chars)
- Pegar imagen desde portapapeles
- Ventana deslizante 10 turnos (conversaciones infinitas)
- **Autenticación Google (Emergent OAuth)** — sesiones privadas por usuario
- **Streaming SSE** — primer chunk visible en ~1.9s
- Mongo indexes: users.email unique, user_sessions.session_token + TTL en expires_at
- Errores HTTP semánticos (402 BUDGET, 429 RATE, 413 CONTEXT, 504 TIMEOUT, 502 LLM)
- Auto-retry, asyncio.wait_for(45s)
- Sin emergentintegrations en runtime (deploy Vercel funciona)

## Backlog
- Drag & drop sobre la ventana
- Múltiples adjuntos por mensaje
- Export conversación a PDF/Markdown
- Modo "Examen" con bloqueo de pistas
- Cleanup automático de sesiones vacías ("Nueva sesión")
