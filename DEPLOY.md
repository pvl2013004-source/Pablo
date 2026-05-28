# Deploy SYVREN — Tutor Metodológico

## ⚠️ Si tu deploy en Vercel falla con `No 'project' table found in pyproject.toml`

Ya está arreglado en este commit (`backend/pyproject.toml` ahora tiene la sección `[project]` que `uv` necesita). Solo tienes que:

1. `Save to GitHub` desde el chat
2. En Vercel → Deployments → **Redeploy** (o se hará solo cuando detecte el push)

---

## Setup recomendado: Vercel monorepo (frontend + backend en una sola plataforma)

### A) Variables de entorno en Vercel

Tu proyecto Vercel está conectado al repo. Asegúrate de que en **Settings → Environment Variables** estén estas 5:

| Key | Value ejemplo | Notas |
|-----|---------------|-------|
| `MONGO_URL` | `mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority` | Atlas connection string |
| `DB_NAME` | `syvren` | |
| `EMERGENT_LLM_KEY` | `sk-emergent-…` | Tu Universal Key |
| `CORS_ORIGINS` | `https://TU-APP.vercel.app` | URL exacta de tu Vercel app, sin slash final |
| `REACT_APP_BACKEND_URL` | `https://TU-APP.vercel.app` | Misma URL (en monorepo el `/api/*` se enruta solo) |

Marca **Production + Preview + Development** en cada una.

### B) MongoDB Atlas (gratis)

1. https://cloud.mongodb.com → registrarse
2. Build a Database → tier **M0 (Free)**
3. Database Access → Add User → guarda usuario y contraseña
4. Network Access → Add IP → `0.0.0.0/0`
5. Connect → Drivers → copia el connection string como `MONGO_URL`

### C) Estructura del repo (cómo Vercel lo lee)

```
/app
├── vercel.json          ← Monorepo: rutea /api/* → backend, resto → frontend build
├── frontend/
│   ├── vercel.json      ← Solo si se despliega el frontend como proyecto aparte
│   ├── package.json
│   ├── public/
│   └── src/
└── backend/
    ├── vercel.json      ← Si se despliega el backend como proyecto aparte
    ├── pyproject.toml   ← ✅ Con [project] table para uv
    ├── requirements.txt ← Backup para hostings que usan pip
    ├── server.py        ← FastAPI app importable como `server:app`
    └── .python-version  ← `3.11`
```

### D) Redeploy

Después de pushear los cambios:
1. Vercel detectará el push y reconstruirá automáticamente
2. Espera 2-4 minutos
3. La build debería decir `✓ Build completed`
4. Verifica:
   - `https://TU-APP.vercel.app/api/` → JSON `{"message": "Tutor Metodológico API"}`
   - `https://TU-APP.vercel.app/` → pantalla de login SYVREN

---

## Alternativa: Backend en Render + Frontend en Vercel (recomendado si Vercel Hobby da timeout)

Vercel Hobby tiene **10s de timeout por función**. Si Claude tarda más, verás 504. En ese caso usa Render Free para el backend.

### Backend en Render
1. https://render.com → New + → **Blueprint**
2. Selecciona el repo → Render lee `backend/render.yaml`
3. Llena las 3 variables `sync: false`:
   - `MONGO_URL`, `EMERGENT_LLM_KEY`, `CORS_ORIGINS=https://TU-APP.vercel.app`
4. Apply → ~2 min → copia la URL `https://syvren-backend.onrender.com`

### Frontend en Vercel
1. En tu proyecto Vercel → Settings → Env Vars
2. `REACT_APP_BACKEND_URL = https://syvren-backend.onrender.com`
3. Redeploy

> Render Free duerme tras 15 min. El frontend ya hace wake-up ping al cargar.

---

## Troubleshooting Vercel

| Error en log | Causa | Solución |
|--------------|-------|----------|
| `No 'project' table found in pyproject.toml` | pyproject.toml antiguo sin `[project]` | ✅ Ya arreglado, redeploy |
| `uv lock failed` | Misma causa que arriba | ✅ Ya arreglado |
| Warning `'builds' existing in config file` | Es informativo, no bloquea | Ignorar |
| `ModuleNotFoundError: emergentintegrations` | requirements.txt viejo | Pull último commit, redeploy |
| Timeout 10s en `/api/chat/.../stream` | Plan Hobby + respuesta lenta | Cambia backend a Render |
| CORS error en navegador | `CORS_ORIGINS` no incluye la URL real | Edita en Settings → Env Vars |
| "Backend no conectado" | Falta `REACT_APP_BACKEND_URL` | Añadir env var + redeploy |

---

## Optimizaciones aplicadas (latest)

✅ **Auth Google (Emergent OAuth)** — sesiones privadas por usuario
✅ **Streaming SSE** — primer chunk visible en ~1.9 s
✅ **Sin `emergentintegrations`** — usa `litellm` puro (PyPI) → Vercel build OK
✅ `pyproject.toml` con `[project]` válido → `uv lock` succeeds en Vercel
✅ Claude Haiku 4.5 (3-5× más rápido que Sonnet, ~5× más barato)
✅ MongoDB indexes + TTL en sesiones expiradas
✅ Errores HTTP semánticos + auto-retry + timeouts 45s
✅ Frontend con dedupe de mensajes en streaming
✅ Sin links externos a Emergent en el HTML servido al usuario
