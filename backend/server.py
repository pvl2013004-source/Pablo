from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Cookie, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict
import httpx
import json
import os
import io
import uuid
import base64 as _b64
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Top-level config (must be importable by Vercel / uvicorn / gunicorn)
MONGO_URL = os.environ.get('MONGO_URL', '')
DB_NAME = os.environ.get('DB_NAME', 'syvren')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
CORS_ORIGINS = [o.strip() for o in os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',') if o.strip()]
# Cookies need explicit allowed credential origins (no wildcard).
COOKIE_ORIGINS = [o for o in CORS_ORIGINS if o != '*']

EMERGENT_AUTH_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
SESSION_DAYS = 7

# Emergent Universal Key talks to this OpenAI-compatible proxy.
EMERGENT_PROXY_URL = 'https://integrations.emergentagent.com/llm'
MODEL_NAME = 'claude-haiku-4-5-20251001'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("syvren")

# FastAPI app instance — defined at module top-level so Vercel / uvicorn / gunicorn can import it.
app = FastAPI(title="SYVREN — Tutor Metodológico API")
api_router = APIRouter(prefix="/api")

# MongoDB (lazy: avoid crashing the module if MONGO_URL is missing at import time)
_mongo_client: Optional[AsyncIOMotorClient] = None


def get_db():
    """Lazily create the Mongo client on first use. Safer for serverless cold starts."""
    global _mongo_client
    if not MONGO_URL:
        return None
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
    return _mongo_client[DB_NAME]


class _DBProxy:
    """Lets existing `db.collection.method(...)` syntax keep working with the lazy client."""
    def __getattr__(self, name):
        actual = get_db()
        if actual is None:
            raise HTTPException(status_code=503, detail="Base de datos no configurada")
        return getattr(actual, name)


db = _DBProxy()
client = None  # kept for backward-compat with shutdown handler

# Tutor system prompts per language
PROMPT_ES = """Rol: Eres un tutor de alta precisión. Tu objetivo es proporcionar datos y guiar el proceso paso a paso sin entregar nunca el resultado final.

Protocolo de Respuesta:
1. Archivo de Datos: información técnica breve (Datos, Técnica, Concepto).
2. Paso Activo (SOLO UNO): la única acción que el usuario debe realizar ahora. No menciones pasos futuros.
3. Acción de Cierre: una pregunta directa o instrucción clara.

REGLA ESPECIAL PARA ARITMÉTICA (sumas, restas, multiplicaciones, divisiones, potencias, raíces):
- Si el cálculo requiere más de un paso mental (ej. 23 × 47, 1098 + 6537, 500 ÷ 12, 17²), DESCOMPÓNLO en sub-pasos triviales.
- Multiplicaciones de dos cifras: aplica el método de descomposición. Ej. 23 × 47 = (20+3) × 47 → primero 20 × 47, luego 3 × 47, luego sumar.
- Sumas/restas grandes: alinea por columnas y avanza una columna por respuesta.
- Divisiones: usa división larga, una cifra del cociente por respuesta.
- Potencias: redúcelas a una multiplicación por respuesta (ej. 3³ → primero 3 × 3, luego ese resultado × 3).
- Cada Paso Activo debe ser tan simple que el usuario lo pueda resolver mentalmente o con cálculo de una sola operación.

Restricciones de Estilo:
- Sin saludos ni frases de relleno.
- Sin emojis.
- Usa negritas solo en datos vitales o en la acción.
- Si el usuario se equivoca, corrige brevemente y repite el paso (no avances).

FORMATO OBLIGATORIO (Markdown, encabezados exactos):

## Archivo de Datos
- (lista breve)

## Paso Activo
(una sola micro-acción)

## Acción de Cierre
(pregunta directa)

NUNCA entregues el resultado final. NUNCA uses emojis. NUNCA uses saludos. RESPONDE SIEMPRE EN ESPAÑOL."""

PROMPT_EN = """Role: You are a high-precision tutor. Your goal is to provide data and guide the process step by step, NEVER delivering the final result.

Response Protocol:
1. Data File: brief technical info (Data, Technique, Concept).
2. Active Step (ONLY ONE): the single action the user must take right now. No future steps.
3. Closing Action: a direct question or clear instruction.

SPECIAL RULE FOR ARITHMETIC (addition, subtraction, multiplication, division, powers, roots):
- If the calculation needs more than one mental step (e.g. 23 × 47, 1098 + 6537, 500 ÷ 12, 17²), BREAK IT DOWN into trivial sub-steps.
- Two-digit multiplication: use decomposition. Ex. 23 × 47 = (20+3) × 47 → first 20 × 47, then 3 × 47, then add.
- Large sums/subtractions: column alignment, one column per turn.
- Divisions: long division, one quotient digit per turn.
- Powers: reduce to one multiplication per turn (e.g. 3³ → first 3 × 3, then result × 3).
- Each Active Step must be solvable mentally or with a single operation.

Style Constraints:
- No greetings or filler phrases.
- No emojis.
- Bold only for vital data or the action.
- If the user makes a mistake, correct briefly and repeat the step.

MANDATORY FORMAT (Markdown, exact headings):

## Data File
- (brief list)

## Active Step
(one micro-action)

## Closing Action
(direct question)

NEVER deliver the final result. NEVER use emojis. NEVER use greetings. ALWAYS RESPOND IN ENGLISH."""

PROMPT_FR = """Rôle : Tu es un tuteur de haute précision. Ton objectif est de fournir des données et de guider le processus étape par étape, sans JAMAIS donner le résultat final.

Protocole de réponse :
1. Fichier de Données : info technique brève (Données, Technique, Concept).
2. Étape Active (UNE SEULE) : la seule action que l'utilisateur doit effectuer maintenant. Pas d'étapes futures.
3. Action de Clôture : une question directe ou une instruction claire.

RÈGLE SPÉCIALE POUR L'ARITHMÉTIQUE (additions, soustractions, multiplications, divisions, puissances, racines) :
- Si le calcul demande plus d'une étape mentale (ex. 23 × 47, 1098 + 6537, 500 ÷ 12, 17²), DÉCOMPOSE-LE en sous-étapes triviales.
- Multiplications à deux chiffres : utilise la décomposition. Ex. 23 × 47 = (20+3) × 47 → d'abord 20 × 47, puis 3 × 47, puis additionner.
- Grandes sommes/soustractions : alignement en colonnes, une colonne par tour.
- Divisions : division longue, un chiffre du quotient par tour.
- Puissances : réduis à une multiplication par tour (ex. 3³ → d'abord 3 × 3, puis ce résultat × 3).
- Chaque Étape Active doit être résoluble mentalement ou avec une seule opération.

Contraintes de Style :
- Pas de salutations ni de phrases de remplissage.
- Pas d'emojis.
- Gras uniquement pour les données vitales ou l'action.
- Si l'utilisateur se trompe, corrige brièvement et répète l'étape.

FORMAT OBLIGATOIRE (Markdown, en-têtes exacts) :

## Fichier de Données
- (liste brève)

## Étape Active
(une seule micro-action)

## Action de Clôture
(question directe)

NE JAMAIS donner le résultat final. PAS d'emojis. PAS de salutations. RÉPONDS TOUJOURS EN FRANÇAIS."""

PROMPT_PT = """Papel: Você é um tutor de alta precisão. Seu objetivo é fornecer dados e guiar o processo passo a passo, NUNCA entregando o resultado final.

Protocolo de Resposta:
1. Arquivo de Dados: informação técnica breve (Dados, Técnica, Conceito).
2. Passo Ativo (APENAS UM): a única ação que o usuário deve realizar agora. Sem passos futuros.
3. Ação de Encerramento: uma pergunta direta ou instrução clara.

REGRA ESPECIAL PARA ARITMÉTICA (somas, subtrações, multiplicações, divisões, potências, raízes):
- Se o cálculo exigir mais de um passo mental (ex. 23 × 47, 1098 + 6537, 500 ÷ 12, 17²), DECOMPONHA em sub-passos triviais.
- Multiplicação de dois dígitos: use decomposição. Ex. 23 × 47 = (20+3) × 47 → primeiro 20 × 47, depois 3 × 47, depois somar.
- Somas/subtrações grandes: alinhe por colunas, uma coluna por turno.
- Divisões: divisão longa, um dígito do quociente por turno.
- Potências: reduza a uma multiplicação por turno (ex. 3³ → primeiro 3 × 3, depois esse resultado × 3).
- Cada Passo Ativo deve ser resolvível mentalmente ou com uma única operação.

Restrições de Estilo:
- Sem saudações ou frases de preenchimento.
- Sem emojis.
- Negrito apenas para dados vitais ou a ação.
- Se o usuário errar, corrija brevemente e repita o passo.

FORMATO OBRIGATÓRIO (Markdown, cabeçalhos exatos):

## Arquivo de Dados
- (lista breve)

## Passo Ativo
(uma única micro-ação)

## Ação de Encerramento
(pergunta direta)

NUNCA entregue o resultado final. SEM emojis. SEM saudações. RESPONDA SEMPRE EM PORTUGUÊS."""

PROMPTS_BY_LANG = {
    "es": PROMPT_ES,
    "en": PROMPT_EN,
    "fr": PROMPT_FR,
    "pt": PROMPT_PT,
}

# Backward-compatible default
TUTOR_SYSTEM_PROMPT = PROMPT_ES


# --- Models ---
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None


class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    image_base64: Optional[str] = None  # only stored on user messages with attachment
    image_mime: Optional[str] = None
    pdf_name: Optional[str] = None
    pdf_pages: Optional[int] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Session(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str = "Nueva sesión"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SendMessageRequest(BaseModel):
    content: str
    language: Optional[str] = "es"
    image_base64: Optional[str] = None  # raw base64 without data: prefix
    image_mime: Optional[str] = None    # e.g. "image/jpeg", "image/png", "image/webp"
    pdf_base64: Optional[str] = None    # raw base64 PDF
    pdf_name: Optional[str] = None


class SendMessageResponse(BaseModel):
    user_message: Message
    assistant_message: Message
    session: Session


class GoogleSessionRequest(BaseModel):
    session_id: str


# --- Auth helper (cookie-first, then Authorization Bearer header) ---
async def get_current_user(
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> User:
    if db is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    token = session_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")

    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Sesión inválida")

    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sesión expirada")

    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return User(**user_doc)


# --- Routes ---
@api_router.get("/")
async def root():
    return {"message": "Tutor Metodológico API"}


# --- Auth routes ---
@api_router.post("/auth/google-session")
async def auth_google_session(payload: GoogleSessionRequest, response: Response):
    """
    Exchange a one-time `session_id` (from Emergent Google Auth URL fragment) for a 7-day
    `session_token`. Stores the user in MongoDB and sets the cookie.
    """
    if get_db() is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    # Call Emergent Auth backend (NEVER do this from the frontend)
    logger.info(f"[auth] Exchanging session_id={payload.session_id[:8]}...")
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.get(
                EMERGENT_AUTH_SESSION_URL,
                headers={"X-Session-ID": payload.session_id},
            )
        logger.info(f"[auth] Emergent returned status={r.status_code}")
        if r.status_code != 200:
            logger.warning(f"[auth] Emergent body: {r.text[:300]}")
            raise HTTPException(status_code=401, detail="Sesión Google inválida")
        data = r.json()
        logger.info(f"[auth] Emergent payload keys: {list(data.keys())}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Emergent auth error")
        raise HTTPException(status_code=502, detail=f"Auth proxy error: {e}")

    email = data.get("email")
    name = data.get("name") or email
    picture = data.get("picture")
    session_token = data.get("session_token")
    if not email or not session_token:
        logger.error(f"[auth] Incomplete: email={bool(email)} session_token={bool(session_token)} keys={list(data.keys())}")
        raise HTTPException(status_code=502, detail="Respuesta auth incompleta")
    logger.info(f"[auth] Success for {email}")

    # Upsert user (find by email — Google accounts are identified by email)
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    if user_doc:
        user_id = user_doc["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture, "last_login": datetime.now(timezone.utc)}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": datetime.now(timezone.utc),
            "last_login": datetime.now(timezone.utc),
        })

    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    })

    # httpOnly cookie + Authorization fallback for cross-origin clients
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=SESSION_DAYS * 24 * 3600,
        path="/",
    )

    return {
        "user": {"user_id": user_id, "email": email, "name": name, "picture": picture},
        "session_token": session_token,
    }


@api_router.get("/auth/me", response_model=User)
async def auth_me(user: User = Depends(get_current_user)):
    return user


@api_router.post("/auth/logout")
async def auth_logout(
    response: Response,
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
):
    token = session_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if token and get_db() is not None:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"ok": True}


@api_router.post("/chat/sessions", response_model=Session)
async def create_session(user: User = Depends(get_current_user)):
    session = Session(user_id=user.user_id)
    await db.sessions.insert_one(session.model_dump())
    return session


@api_router.get("/chat/sessions", response_model=List[Session])
async def list_sessions(user: User = Depends(get_current_user)):
    sessions = (
        await db.sessions.find({"user_id": user.user_id}, {"_id": 0})
        .sort("updated_at", -1)
        .to_list(500)
    )
    return sessions


@api_router.get("/chat/sessions/{session_id}/messages", response_model=List[Message])
async def get_messages(session_id: str, user: User = Depends(get_current_user)):
    # Verify ownership
    sess = await db.sessions.find_one({"id": session_id, "user_id": user.user_id}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    messages = (
        await db.messages.find({"session_id": session_id}, {"_id": 0})
        .sort("timestamp", 1)
        .to_list(2000)
    )
    return messages


@api_router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str, user: User = Depends(get_current_user)):
    result = await db.sessions.delete_one({"id": session_id, "user_id": user.user_id})
    if result.deleted_count:
        await db.messages.delete_many({"session_id": session_id})
    return {"ok": True}


@api_router.post("/chat/sessions/{session_id}/message", response_model=SendMessageResponse)
async def send_message(session_id: str, payload: SendMessageRequest, user: User = Depends(get_current_user)):
    session = await db.sessions.find_one({"id": session_id, "user_id": user.user_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key no configurada")

    user_text = payload.content.strip()
    if not user_text and not payload.image_base64 and not payload.pdf_base64:
        raise HTTPException(status_code=400, detail="Mensaje vacío")

    # Normalize image base64 (strip data URI prefix if present)
    img_b64 = payload.image_base64
    img_mime = payload.image_mime
    if img_b64 and img_b64.startswith("data:"):
        try:
            header, b64data = img_b64.split(",", 1)
            img_b64 = b64data
            if not img_mime and "image/" in header:
                img_mime = header.split(";")[0].replace("data:", "")
        except Exception:
            pass
    if img_b64 and not img_mime:
        img_mime = "image/jpeg"
    if img_mime and img_mime not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Formato de imagen no soportado (usa JPEG, PNG o WEBP)")

    # PDF: extract text content
    pdf_text = ""
    pdf_pages = None
    pdf_name = payload.pdf_name
    if payload.pdf_base64:
        try:
            pdf_b64 = payload.pdf_base64
            if pdf_b64.startswith("data:"):
                pdf_b64 = pdf_b64.split(",", 1)[1]
            pdf_bytes = _b64.b64decode(pdf_b64)
            if len(pdf_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="PDF demasiado grande (máx 10 MB)")
            from pypdf import PdfReader  # lazy import to keep cold start light
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pdf_pages = len(reader.pages)
            extracted = []
            for i, page in enumerate(reader.pages[:50]):  # cap at 50 pages
                try:
                    extracted.append(f"[Página {i+1}]\n{page.extract_text() or ''}")
                except Exception:
                    pass
            pdf_text = "\n\n".join(extracted).strip()
            MAX_PDF_CHARS = 12000
            if len(pdf_text) > MAX_PDF_CHARS:
                pdf_text = pdf_text[:MAX_PDF_CHARS] + "\n\n[...contenido truncado para mantener la conversación eficiente...]"
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No se pudo leer el PDF: {str(e)}")

    # If only attachment (no text), inject a default question in the right language
    if not user_text and (img_b64 or pdf_text):
        default_q = {
            "es": "Analiza este material y guíame paso a paso para resolverlo o entenderlo.",
            "en": "Analyze this material and guide me step by step to solve or understand it.",
            "fr": "Analyse ce document et guide-moi étape par étape pour le résoudre ou le comprendre.",
            "pt": "Analise este material e me guie passo a passo para resolvê-lo ou entendê-lo.",
        }
        user_text = default_q.get((payload.language or "es").lower(), default_q["es"])

    # Compose the text sent to the model (include PDF content if present)
    model_user_text = user_text
    if pdf_text:
        model_user_text = (
            f"{user_text}\n\n---\nContenido del documento adjunto"
            + (f" ({pdf_name})" if pdf_name else "")
            + f" — {pdf_pages or '?'} páginas:\n\n{pdf_text}"
        )

    # Persist user message first (with attachments metadata)
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=user_text,
        image_base64=img_b64,
        image_mime=img_mime,
        pdf_name=pdf_name if pdf_text else None,
        pdf_pages=pdf_pages if pdf_text else None,
    )
    # Persist user message AND fetch history in parallel (saves ~50-100ms)
    insert_user_task = db.messages.insert_one(user_msg.model_dump())
    HISTORY_TURNS = 10  # last 10 user + 10 assistant messages (tight window → fast + cheap)
    MAX_MSG_CHARS = 1200  # truncate any single past message body
    fetch_history_task = (
        db.messages.find(
            {"session_id": session_id},
            {"_id": 0, "image_base64": 0, "pdf_pages": 0, "timestamp": 0},
        )
        .sort("timestamp", -1)
        .to_list(HISTORY_TURNS * 2)
    )
    _, history_msgs = await asyncio.gather(insert_user_task, fetch_history_task)
    history_msgs.reverse()

    history_text_parts = []
    for m in history_msgs:
        body = (m.get("content") or "").strip()
        if len(body) > MAX_MSG_CHARS:
            body = body[:MAX_MSG_CHARS] + " …[truncado]"
        tag = "[Usuario]" if m["role"] == "user" else "[Tutor]"
        if m.get("pdf_name"):
            tag += f" (PDF: {m['pdf_name']})"
        history_text_parts.append(f"{tag}: {body}")
    history_block = "\n\n".join(history_text_parts)

    system_message = PROMPTS_BY_LANG.get((payload.language or "es").lower(), PROMPT_ES)
    if history_block:
        system_message = system_message + "\n\nHistorial reciente / Recent history:\n" + history_block

    # Build OpenAI-compatible messages payload for litellm.
    # Emergent Universal Key is routed to the proxy via api_base; provider header is forced to "openai".
    chat_messages: List[dict] = [{"role": "system", "content": system_message}]
    if img_b64:
        # Detect mime from base64 prefix if not provided
        mime = img_mime or "image/jpeg"
        chat_messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": model_user_text},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
            ],
        })
    else:
        chat_messages.append({"role": "user", "content": model_user_text})

    async def _do_send():
        # Direct httpx POST to Emergent's OpenAI-compatible proxy. Avoids litellm bloat (Vercel-friendly).
        async with httpx.AsyncClient(timeout=40) as http:
            r = await http.post(
                f"{EMERGENT_PROXY_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {EMERGENT_LLM_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": MODEL_NAME, "messages": chat_messages},
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    response_text = None
    for attempt in range(2):
        try:
            response_text = await asyncio.wait_for(_do_send(), timeout=45)
            break
        except asyncio.TimeoutError:
            logger.warning("LLM timeout (>45s)")
            if attempt == 0:
                continue
            raise HTTPException(status_code=504, detail="LLM_TIMEOUT")
        except httpx.HTTPStatusError as e:
            err_text = (e.response.text or "").lower()
            status = e.response.status_code
            if status == 402 or "budget" in err_text or "exceeded" in err_text or "insufficient" in err_text:
                raise HTTPException(status_code=402, detail="BUDGET_EXCEEDED")
            if status == 429 or "rate" in err_text:
                if attempt == 0:
                    await asyncio.sleep(2)
                    continue
                raise HTTPException(status_code=429, detail="RATE_LIMIT")
            if "context" in err_text and ("length" in err_text or "window" in err_text or "tokens" in err_text):
                raise HTTPException(status_code=413, detail="CONTEXT_TOO_LONG")
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            logger.exception("LLM HTTP error")
            raise HTTPException(status_code=502, detail="LLM_ERROR")
        except Exception:
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            logger.exception("LLM error")
            raise HTTPException(status_code=502, detail="LLM_ERROR")

    if not response_text:
        raise HTTPException(status_code=502, detail="LLM_ERROR")

    assistant_msg = Message(session_id=session_id, role="assistant", content=str(response_text))

    # Persist assistant + update session in parallel (saves ~50-100ms)
    new_title = session.get("title", "Nueva sesión")
    if new_title == "Nueva sesión":
        clean_title = " ".join(user_text.split())
        new_title = clean_title[:60] + ("…" if len(clean_title) > 60 else "")
    now = datetime.now(timezone.utc).isoformat()
    await asyncio.gather(
        db.messages.insert_one(assistant_msg.model_dump()),
        db.sessions.update_one(
            {"id": session_id},
            {"$set": {"title": new_title, "updated_at": now}},
        ),
    )

    # Build updated session dict locally instead of round-tripping to MongoDB
    updated_session = {**session, "title": new_title, "updated_at": now}

    return SendMessageResponse(
        user_message=user_msg,
        assistant_message=assistant_msg,
        session=Session(**updated_session),
    )


# --- Streaming variant: emits SSE chunks while Claude generates ---
@api_router.post("/chat/sessions/{session_id}/stream")
async def stream_message(
    session_id: str,
    payload: SendMessageRequest,
    user: User = Depends(get_current_user),
):
    session = await db.sessions.find_one({"id": session_id, "user_id": user.user_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key no configurada")

    user_text = (payload.content or "").strip()
    img_b64 = payload.image_base64
    img_mime = payload.image_mime
    if img_b64 and img_b64.startswith("data:"):
        try:
            header, b64data = img_b64.split(",", 1)
            img_b64 = b64data
            if not img_mime and "image/" in header:
                img_mime = header.split(";")[0].replace("data:", "")
        except Exception:
            pass
    if img_b64 and not img_mime:
        img_mime = "image/jpeg"

    if not user_text and not img_b64 and not payload.pdf_base64:
        raise HTTPException(status_code=400, detail="Mensaje vacío")

    # PDF extraction (same as send_message)
    pdf_text = ""
    pdf_pages = None
    pdf_name = payload.pdf_name
    if payload.pdf_base64:
        try:
            pdf_b64 = payload.pdf_base64.split(",", 1)[-1] if payload.pdf_base64.startswith("data:") else payload.pdf_base64
            pdf_bytes = _b64.b64decode(pdf_b64)
            if len(pdf_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="PDF demasiado grande (máx 10 MB)")
            from pypdf import PdfReader  # lazy import to keep cold start light
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pdf_pages = len(reader.pages)
            extracted = [f"[Página {i+1}]\n{p.extract_text() or ''}" for i, p in enumerate(reader.pages[:50])]
            pdf_text = "\n\n".join(extracted).strip()
            if len(pdf_text) > 12000:
                pdf_text = pdf_text[:12000] + "\n\n[...truncado...]"
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No se pudo leer el PDF: {e}")

    if not user_text and (img_b64 or pdf_text):
        defaults = {
            "es": "Analiza este material y guíame paso a paso.",
            "en": "Analyze this material and guide me step by step.",
            "fr": "Analyse ce document et guide-moi étape par étape.",
            "pt": "Analise este material e me guie passo a passo.",
        }
        user_text = defaults.get((payload.language or "es").lower(), defaults["es"])

    model_user_text = user_text
    if pdf_text:
        model_user_text = f"{user_text}\n\n---\nContenido del documento{(' (' + pdf_name + ')') if pdf_name else ''} — {pdf_pages or '?'} páginas:\n\n{pdf_text}"

    user_msg = Message(
        session_id=session_id, role="user", content=user_text,
        image_base64=img_b64, image_mime=img_mime,
        pdf_name=pdf_name if pdf_text else None, pdf_pages=pdf_pages if pdf_text else None,
    )

    insert_user_task = db.messages.insert_one(user_msg.model_dump())
    fetch_history_task = (
        db.messages.find(
            {"session_id": session_id},
            {"_id": 0, "image_base64": 0, "pdf_pages": 0, "timestamp": 0},
        ).sort("timestamp", -1).to_list(20)
    )
    _, history_msgs = await asyncio.gather(insert_user_task, fetch_history_task)
    history_msgs.reverse()
    parts = []
    for m in history_msgs:
        body = (m.get("content") or "").strip()
        if len(body) > 1200:
            body = body[:1200] + " …[truncado]"
        tag = "[Usuario]" if m["role"] == "user" else "[Tutor]"
        if m.get("pdf_name"):
            tag += f" (PDF: {m['pdf_name']})"
        parts.append(f"{tag}: {body}")
    history_block = "\n\n".join(parts)

    system_message = PROMPTS_BY_LANG.get((payload.language or "es").lower(), PROMPT_ES)
    if history_block:
        system_message = system_message + "\n\nHistorial reciente / Recent history:\n" + history_block

    chat_messages = [{"role": "system", "content": system_message}]
    if img_b64:
        chat_messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": model_user_text},
                {"type": "image_url", "image_url": {"url": f"data:{img_mime or 'image/jpeg'};base64,{img_b64}"}},
            ],
        })
    else:
        chat_messages.append({"role": "user", "content": model_user_text})

    async def event_gen():
        # Send the user-message metadata immediately so the client can render it
        yield f"data: {json.dumps({'type': 'user', 'message': user_msg.model_dump()})}\n\n"

        accumulated = ""
        try:
            async with httpx.AsyncClient(timeout=60) as http:
                async with http.stream(
                    "POST",
                    f"{EMERGENT_PROXY_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {EMERGENT_LLM_KEY}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                    json={"model": MODEL_NAME, "messages": chat_messages, "stream": True},
                ) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", errors="ignore").lower()
                        if resp.status_code == 402 or "budget" in body or "exceeded" in body or "insufficient" in body:
                            yield f"data: {json.dumps({'type': 'error', 'code': 'BUDGET_EXCEEDED'})}\n\n"
                            return
                        yield f"data: {json.dumps({'type': 'error', 'code': 'LLM_ERROR', 'detail': body[:200]})}\n\n"
                        return
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            evt = json.loads(payload)
                            delta = evt.get("choices", [{}])[0].get("delta", {})
                            text = delta.get("content") or ""
                        except Exception:
                            text = ""
                        if text:
                            accumulated += text
                            yield f"data: {json.dumps({'type': 'chunk', 'text': text})}\n\n"
        except Exception as e:
            err_str = str(e).lower()
            if "budget" in err_str or "exceeded" in err_str or "insufficient" in err_str:
                yield f"data: {json.dumps({'type': 'error', 'code': 'BUDGET_EXCEEDED'})}\n\n"
                return
            yield f"data: {json.dumps({'type': 'error', 'code': 'LLM_ERROR', 'detail': str(e)[:200]})}\n\n"
            return

        if not accumulated:
            yield f"data: {json.dumps({'type': 'error', 'code': 'EMPTY'})}\n\n"
            return

        assistant_msg = Message(session_id=session_id, role="assistant", content=accumulated)
        new_title = session.get("title", "Nueva sesión")
        if new_title == "Nueva sesión":
            clean = " ".join(user_text.split())
            new_title = clean[:60] + ("…" if len(clean) > 60 else "")
        now = datetime.now(timezone.utc).isoformat()
        await asyncio.gather(
            db.messages.insert_one(assistant_msg.model_dump()),
            db.sessions.update_one(
                {"id": session_id, "user_id": user.user_id},
                {"$set": {"title": new_title, "updated_at": now}},
            ),
        )
        updated_session = {**session, "title": new_title, "updated_at": now}
        yield f"data: {json.dumps({'type': 'done', 'assistant': assistant_msg.model_dump(), 'session': Session(**updated_session).model_dump()})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )



app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    # cookies require credentials=True + explicit origins (no wildcard)
    allow_credentials=True,
    allow_origins=COOKIE_ORIGINS if COOKIE_ORIGINS else CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)


@app.on_event("startup")
async def startup_db():
    if get_db() is None:
        logger.warning("MONGO_URL not set — MongoDB is disabled, only /api/ root will respond.")
        return
    try:
        await db.messages.create_index([("session_id", 1), ("timestamp", -1)])
        await db.sessions.create_index("updated_at")
        await db.sessions.create_index([("user_id", 1), ("updated_at", -1)])
        await db.users.create_index("email", unique=True)
        await db.users.create_index("user_id", unique=True)
        await db.user_sessions.create_index("session_token", unique=True)
        await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
        logger.info("MongoDB indexes ensured.")
    except Exception as e:
        logger.warning(f"Could not create indexes: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
