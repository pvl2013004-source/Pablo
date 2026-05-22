# Deploy SYVREN — Tutor Metodológico

Tu frontend ya está en Vercel (`syvren3.vercel.app`). Para que funcione necesitas el **backend desplegado** + **MongoDB en la nube** + **variable de entorno** en Vercel apuntando al backend.

---

## 1. MongoDB Atlas (gratis, 512 MB)

1. Entra a https://cloud.mongodb.com → crea cuenta gratis
2. Create cluster → tier **M0 (Free)** → región más cercana a ti
3. Database Access → Add user → guarda usuario y contraseña
4. Network Access → Add IP → `0.0.0.0/0` (permitir desde cualquier IP)
5. Connect → Drivers → copia la **connection string**, algo como:
   ```
   mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

---

## 2. Backend en Render (gratis, plan starter)

1. Entra a https://render.com → New + → **Web Service**
2. Conecta tu repo de GitHub (haz "Save to GitHub" desde el chat de Emergent primero)
3. Configuración:
   - **Root directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Instance type:** Free
4. **Variables de entorno** (Advanced → Add Environment Variable):
   - `MONGO_URL` = la connection string de Atlas
   - `DB_NAME` = `syvren`
   - `EMERGENT_LLM_KEY` = tu clave universal (la del .env actual)
   - `CORS_ORIGINS` = `https://syvren3.vercel.app` (tu URL exacta de Vercel)
   - `PYTHON_VERSION` = `3.11.10`
5. Create Web Service → espera 2-3 minutos
6. Cuando termine, copia la URL que te dan (ej. `https://syvren-backend.onrender.com`)
7. Verifica que funciona: abre `https://syvren-backend.onrender.com/api/` → debe responder JSON

> ⚠️ **Render Free duerme tras 15 min sin uso.** La primera petición tarda ~30 s en despertar. Si quieres "always on" usa Railway ($5/mes) o Fly.io.

---

## 3. Vercel — apuntar al backend

1. Entra a tu proyecto en Vercel → Settings → Environment Variables
2. Añade:
   - **Key:** `REACT_APP_BACKEND_URL`
   - **Value:** la URL de Render sin slash final (ej. `https://syvren-backend.onrender.com`)
   - **Environments:** marca Production, Preview, Development
3. Settings → Deployments → redeploy el último → Vercel re-construirá con la nueva variable
4. Abre `syvren3.vercel.app` → ya debe conectarse al backend

---

## 4. Verificación rápida

Si sigue dando "Error: no se pudo obtener respuesta del modelo":

1. Abre la consola del navegador (F12) en la pestaña Network
2. Envía un mensaje en SYVREN
3. Mira la petición a `/api/chat/sessions/.../message`:
   - **Status 0 / CORS error** → el backend `CORS_ORIGINS` no incluye tu URL de Vercel
   - **Status 502** → backend caído o despertando (espera 30 s y reintenta)
   - **Status 402** → saldo agotado en Universal Key → recarga
   - **Status 404 sobre /api/...** → REACT_APP_BACKEND_URL incorrecta

---

## Alternativas al backend en Render

| Plataforma | Costo | Always-on | Setup |
|------------|-------|-----------|-------|
| **Render Free** | $0 | ❌ duerme 15min | Sí |
| Railway | ~$5/mes | ✅ | Sí |
| Fly.io | ~$3/mes | ✅ | Usa Dockerfile incluido |
| Google Cloud Run | Pay-per-use (~$0-2/mes) | Cold start | Usa Dockerfile |

Para Fly.io / Cloud Run / Railway: usa el `Dockerfile` que ya está en `/app/backend/`.

---

## Optimizaciones de rendimiento aplicadas

✅ Ventana deslizante de 20 turnos (en vez de historial infinito)
✅ Escrituras a MongoDB paralelizadas con `asyncio.gather` (-100 ms/turno)
✅ History fetch excluye `image_base64` (reduce ancho de banda 10-100×)
✅ Sin re-fetch de sesión después del update (ahorra 1 query)
✅ CORS preflight cacheado 24 h (`max_age=86400`)
✅ Reintento automático ante errores transitorios
