# Deploy SYVREN — Tutor Metodológico

Tu frontend ya está en Vercel. Para que funcione necesitas: **backend en Render** + **MongoDB Atlas** + **variable de entorno en Vercel**.

---

## ⚠️ IMPORTANTE — Razón por la que falla el deploy

El paquete `emergentintegrations` **NO está en PyPI**. Está en una CDN privada.
Por eso `pip install -r requirements.txt` falla en cualquier hosting estándar.

La solución (ya configurada en `render.yaml`, `Procfile` y `pip.conf`):

```
pip install -r requirements.txt --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

Render usa automáticamente el `buildCommand` de `render.yaml`, así que si despliegas con "Blueprint" no tienes que hacer nada manual.

---

## 1. MongoDB Atlas (gratis, 512 MB)

1. https://cloud.mongodb.com → crea cuenta
2. Build a Database → tier **M0 (Free)** → región cercana
3. Database Access → Add User → guarda usuario y contraseña
4. Network Access → Add IP → `0.0.0.0/0`
5. Connect → Drivers → copia la connection string:
   ```
   mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

---

## 2. Backend en Render (gratis)

### Opción A — Blueprint (recomendado, 1 clic)
1. https://render.com → New + → **Blueprint**
2. Conecta tu repo de GitHub
3. Render detecta `backend/render.yaml` automáticamente
4. Pega los valores de las variables marcadas `sync: false`:
   - `MONGO_URL` = connection string de Atlas
   - `EMERGENT_LLM_KEY` = `sk-emergent-...` (la del .env actual)
   - `CORS_ORIGINS` = `https://syvren3.vercel.app` (tu URL exacta de Vercel)
5. Apply → espera 3-5 minutos

### Opción B — Manual
1. New + → **Web Service** → conecta repo
2. Configuración:
   - **Root directory:** `backend`
   - **Build Command:**
     ```
     pip install --upgrade pip && pip install -r requirements.txt --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
     ```
   - **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Instance:** Free
3. Environment Variables: mismas 4 + `PYTHON_VERSION=3.11.10`
4. Create Web Service

### Verifica
Cuando termine, abre `https://tu-app.onrender.com/api/` → debe responder JSON:
```json
{"message": "Tutor Metodológico API"}
```

> ⚠️ **Render Free duerme tras 15 min sin uso** y tarda ~30s en despertar. La app ya tiene un **wake-up ping** al cargar para minimizar la espera.

---

## 3. Vercel — apuntar al backend

1. Vercel → tu proyecto → Settings → Environment Variables
2. Añade:
   - **Key:** `REACT_APP_BACKEND_URL`
   - **Value:** la URL de Render sin slash final (ej. `https://syvren-backend.onrender.com`)
   - **Environments:** Production + Preview + Development
3. Deployments → último deploy → **Redeploy**
4. Abre `syvren3.vercel.app` → conectado ✅

---

## 4. Troubleshooting

| Síntoma | Causa | Solución |
|---------|-------|----------|
| "Backend no conectado" | Falta `REACT_APP_BACKEND_URL` en Vercel | Añádela y redeploy |
| Error 502 / Network | Backend dormido (cold start) | Espera 30 s y reintenta |
| Error 402 / "Saldo agotado" | Universal Key sin saldo | Profile → Universal Key → Add Balance |
| CORS error en consola | `CORS_ORIGINS` no incluye tu Vercel URL | Edita variable en Render |
| Build falla con `emergentintegrations` | Falta `--extra-index-url` | Usa Blueprint (render.yaml ya lo tiene) |

---

## 5. Alternativas al hosting de Render Free

| Plataforma | Costo | Always-on | Setup |
|------------|-------|-----------|-------|
| **Render Free** | $0 | ❌ duerme 15min | render.yaml |
| Railway | ~$5/mes | ✅ | usa Dockerfile |
| Fly.io | ~$3/mes | ✅ | usa Dockerfile |
| Cloud Run | Pay-per-use | Cold start | usa Dockerfile |

Para Railway / Fly.io / Cloud Run usa el `Dockerfile` que ya está en `/app/backend/` — ya incluye la `--extra-index-url`.

---

## 6. Optimizaciones aplicadas

✅ **Modelo Claude Haiku 4.5** (3-5× más rápido que Sonnet, ~5× más barato)
✅ **Ventana deslizante de 10 turnos** (conversaciones infinitas, contexto bounded)
✅ **Escrituras MongoDB en paralelo** (`asyncio.gather`)
✅ **History excluye `image_base64`** (10-100× menos payload)
✅ **CORS preflight cacheado 24 h**
✅ **Wake-up ping al cargar la app** (despierta Render dormido proactivamente)
✅ **Timeout cliente 90 s** (cubre cold start + respuesta larga)
✅ **Reintento automático** ante errores transitorios
✅ **Mensajes de error específicos** (saldo, rate-limit, contexto, red)
✅ **Sin tracking de PostHog ni links a Emergent** en el HTML
✅ **`React.memo`** en mensajes (sin re-render por tecleo)
✅ **requirements.txt minimal** (9 paquetes vs 124 antes) → instala en ~45 s en Render
