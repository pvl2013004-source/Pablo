from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from pypdf import PdfReader
import base64 as _b64
import io
import asyncio


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

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

app = FastAPI()
api_router = APIRouter(prefix="/api")


# --- Models ---
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


# --- Routes ---
@api_router.get("/")
async def root():
    return {"message": "Tutor Metodológico API"}


@api_router.post("/chat/sessions", response_model=Session)
async def create_session():
    session = Session()
    await db.sessions.insert_one(session.model_dump())
    return session


@api_router.get("/chat/sessions", response_model=List[Session])
async def list_sessions():
    sessions = await db.sessions.find({}, {"_id": 0}).sort("updated_at", -1).to_list(500)
    return sessions


@api_router.get("/chat/sessions/{session_id}/messages", response_model=List[Message])
async def get_messages(session_id: str):
    messages = await db.messages.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", 1).to_list(2000)
    return messages


@api_router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str):
    await db.sessions.delete_one({"id": session_id})
    await db.messages.delete_many({"session_id": session_id})
    return {"ok": True}


@api_router.post("/chat/sessions/{session_id}/message", response_model=SendMessageResponse)
async def send_message(session_id: str, payload: SendMessageRequest):
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
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
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pdf_pages = len(reader.pages)
            extracted = []
            for i, page in enumerate(reader.pages[:50]):  # cap at 50 pages
                try:
                    extracted.append(f"[Página {i+1}]\n{page.extract_text() or ''}")
                except Exception:
                    pass
            pdf_text = "\n\n".join(extracted).strip()
            if len(pdf_text) > 20000:
                pdf_text = pdf_text[:20000] + "\n\n[...contenido truncado para mantener la conversación eficiente...]"
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

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_message,
    ).with_model("anthropic", "claude-haiku-4-5-20251001")

    # Send with one automatic retry for transient errors
    async def _do_send():
        if img_b64:
            return await chat.send_message(
                UserMessage(text=model_user_text, file_contents=[ImageContent(image_base64=img_b64)])
            )
        return await chat.send_message(UserMessage(text=model_user_text))

    response_text = None
    last_err = None
    for attempt in range(2):
        try:
            response_text = await _do_send()
            break
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            # Classify error → return a friendly HTTP status the frontend can interpret
            if "budget" in err_str or "exceeded" in err_str or "insufficient" in err_str:
                logger.warning(f"LLM budget exceeded: {e}")
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail="BUDGET_EXCEEDED",
                )
            if "rate" in err_str and "limit" in err_str:
                if attempt == 0:
                    await asyncio.sleep(2)
                    continue
                raise HTTPException(status_code=429, detail="RATE_LIMIT")
            if "context" in err_str and ("length" in err_str or "window" in err_str or "tokens" in err_str):
                raise HTTPException(status_code=413, detail="CONTEXT_TOO_LONG")
            # Network / transient → retry once
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            logger.exception("LLM error")
            raise HTTPException(status_code=502, detail="LLM_ERROR")

    if response_text is None:
        raise HTTPException(status_code=502, detail="LLM_ERROR")

    assistant_msg = Message(session_id=session_id, role="assistant", content=str(response_text))

    # Persist assistant + update session in parallel (saves ~50-100ms)
    new_title = session.get("title", "Nueva sesión")
    if new_title == "Nueva sesión":
        new_title = user_text[:60] + ("…" if len(user_text) > 60 else "")
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


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,  # using "*" origins requires credentials=False
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # cache CORS preflight for 24h → reduces lag
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
