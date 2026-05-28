# Deploy SYVREN — Tutor Metodológico

## ✅ Cambio crítico

El backend YA NO usa `emergentintegrations` (estaba bloqueando deploys porque no está en PyPI).
Ahora usa `litellm` directo → **deploy funciona en Vercel, Render, Railway, Fly.io sin trucos**.
La Universal Key (`sk-emergent-…`) sigue funcionando — apunta al proxy `https://integrations.emergentagent.com/llm`.

---

## Opción A — Todo en Vercel (1 sola plataforma, recomendado)

### A1) Despliegue como monorepo (1 sola URL para frontend + backend)

1. **Save to GitHub** desde el chat de Emergent
2. https://vercel.com → New Project → conecta el repo
3. Vercel detecta automáticamente el `vercel.json` de la raíz
4. **Settings → Environment Variables** añade:
   - `MONGO_URL` = connection string de MongoDB Atlas
   - `DB_NAME` = `syvren`
   - `EMERGENT_LLM_KEY` = `sk-emergent-…`
   - `CORS_ORIGINS` = `https://TU-APP.vercel.app` (la propia URL de Vercel)
5. **NO** definas `REACT_APP_BACKEND_URL` (en monorepo es la misma URL)
   - Pero como el código lo requiere para arrancar, ponlo a `https://TU-APP.vercel.app`
6. Deploy → listo, una sola URL para todo

### A2) Despliegue backend como proyecto Vercel separado

1. Crea otro proyecto Vercel apuntando al mismo repo
2. **Root Directory:** `backend`
3. Variables: `MONGO_URL`, `DB_NAME`, `EMERGENT_LLM_KEY`, `CORS_ORIGINS`
4. Deploy → obtienes URL `https://syvren-api.vercel.app`
5. En el proyecto Vercel del frontend (`syvren3.vercel.app`):
   - **Settings → Env Vars** → `REACT_APP_BACKEND_URL` = `https://syvren-api.vercel.app`
   - Redeploy

### ⚠️ Límites de Vercel para backend Python
- **Hobby (free):** función máx 10s, no apta para Claude (puede tardar 2-4s, OK pero apretado)
- **Pro ($20/mes):** función máx 60s, holgado para Claude

Si te quedas en Hobby y a veces ves error 504, usa Render (Opción B).

---

## Opción B — Frontend en Vercel, Backend en Render (gratis, sin límite de 10s)

### B1) MongoDB Atlas
1. https://cloud.mongodb.com → Cluster M0 (free)
2. Network Access → `0.0.0.0/0`
3. Copia la connection string

### B2) Backend en Render
1. https://render.com → New Blueprint → conecta el repo
2. Render detecta `backend/render.yaml` automáticamente
3. Pega valores de variables `sync: false`:
   - `MONGO_URL`, `EMERGENT_LLM_KEY`, `CORS_ORIGINS=https://syvren3.vercel.app`
4. Apply → ~2 min
5. Copia la URL (ej. `https://syvren-backend.onrender.com`)
6. Verifica: `https://syvren-backend.onrender.com/api/` debe responder JSON

> Render Free duerme tras 15 min de inactividad. El frontend ya hace wake-up ping al cargar.

### B3) Vercel — apuntar al backend
1. En tu proyecto de frontend en Vercel → Settings → Env Vars
2. `REACT_APP_BACKEND_URL` = la URL de Render
3. Redeploy

---

## MongoDB Atlas — obligatorio en cualquier opción

1. https://cloud.mongodb.com → registro gratis
2. Build a Database → **M0 Free**
3. Database Access → crear usuario y contraseña
4. Network Access → Add IP → `0.0.0.0/0`
5. Connect → Drivers → copia el URI:
   ```
   mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

---

## Variables de entorno requeridas

| Variable | Valor ejemplo | Dónde |
|----------|--------------|-------|
| `MONGO_URL` | `mongodb+srv://…` | Backend (Vercel/Render) |
| `DB_NAME` | `syvren` | Backend |
| `EMERGENT_LLM_KEY` | `sk-emergent-…` | Backend |
| `CORS_ORIGINS` | `https://syvren3.vercel.app` | Backend |
| `REACT_APP_BACKEND_URL` | `https://…onrender.com` o `https://…vercel.app` | Frontend |

---

## Troubleshooting Vercel

| Síntoma en Vercel logs | Causa | Solución |
|------------------------|-------|----------|
| `ModuleNotFoundError: No module named 'emergentintegrations'` | requirements.txt viejo | Pull último commit, redeploy |
| `MONGO_URL` KeyError | Falta variable | Añadir en Vercel Env |
| Timeout 10s en `/api/chat/.../message` | Plan Hobby + respuesta lenta | Cambia a Render o sube a Pro |
| CORS error en navegador | `CORS_ORIGINS` no incluye la URL real | Edita y redeploy |
| Build falla al instalar `litellm` | Versión Python | Confirma `runtime.txt` = `python-3.11.10` |

---

## Optimizaciones aplicadas en este pase

✅ `emergentintegrations` reemplazado por `litellm` directo (PyPI) → Vercel build OK
✅ `app = FastAPI()` y `api_router` definidos UNA vez al top-level → importable por Vercel
✅ Imports limpios, sin duplicados
✅ `asyncio.wait_for(_do_send(), timeout=45)` → ninguna request se cuelga indefinidamente
✅ Títulos limpios: `" ".join(user_text.split())` (sin saltos de línea raros)
✅ MongoDB indexes en startup: `(session_id, timestamp)` y `updated_at`
✅ PDF cap reducido 20000 → **12000** chars (más rápido + más barato)
✅ Startup no crashea si falta `MONGO_URL` (responde `/api/` igual)
✅ Modelo Claude Haiku 4.5 → ~1.5-2.5 s por turno
✅ Ventana deslizante 10 turnos · history sin `image_base64` · escrituras paralelas
✅ `pyproject.toml` con `[tool.vercel] entrypoint = "server:app"`
✅ `vercel.json` para backend solo + `vercel.json` raíz para monorepo
✅ `Procfile`, `Dockerfile`, `render.yaml`, `runtime.txt` para hostings alternativos
✅ Frontend: timeout 90s en axios, wake-up ping, pantalla de "Backend no conectado"
