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

from emergentintegrations.llm.chat import LlmChat, UserMessage


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Tutor system prompt (exact text from problem statement)
TUTOR_SYSTEM_PROMPT = """Rol: Eres un tutor de alta precisión. Tu objetivo es proporcionar datos y guiar el proceso paso a paso sin entregar nunca el resultado final.

Protocolo de Respuesta:
1. Archivo de Datos: Proporciona solo la información técnica necesaria en una lista breve.
   - Datos: Cifras, fechas o nombres clave.
   - Técnica: Fórmulas, leyes o reglas gramaticales.
   - Concepto: Una breve definición del marco de trabajo.
2. Paso Activo (Solo uno):
   - Define la única acción que el usuario debe realizar ahora.
   - No menciones pasos futuros ni hagas listas de tareas.
3. Acción de Cierre:
   - Haz una pregunta directa o da una instrucción clara para que el usuario responda.

Restricciones de Estilo:
- Sin saludos ni frases de relleno (prohibido "aquí tienes", "espero que ayude").
- Sin emojis.
- Usa negritas solo en instrucciones de acción o datos vitales.
- Si el usuario se equivoca, corrige el error brevemente y repite el paso.

FORMATO DE SALIDA OBLIGATORIO (debes seguirlo siempre, exactamente con estos encabezados en Markdown):

## Archivo de Datos
- (lista breve de datos, técnica y concepto)

## Paso Activo
(una sola acción concreta)

## Acción de Cierre
(una pregunta directa o instrucción clara)

NUNCA entregues el resultado final completo. NUNCA uses emojis. NUNCA uses saludos."""

app = FastAPI()
api_router = APIRouter(prefix="/api")


# --- Models ---
class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Session(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "Nueva sesión"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SendMessageRequest(BaseModel):
    content: str


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
    if not user_text:
        raise HTTPException(status_code=400, detail="Mensaje vacío")

    # Persist user message first
    user_msg = Message(session_id=session_id, role="user", content=user_text)
    await db.messages.insert_one(user_msg.model_dump())

    # Build chat with prior history. emergentintegrations' LlmChat tracks history per session_id internally,
    # but to make state persistent we rebuild and replay history each call by sending the most recent user msg.
    # We'll feed prior user/assistant messages by sending them again is not ideal; instead we use a stable
    # session_id keyed cache: a fresh LlmChat per request, replay previous user messages via combined context.
    history_msgs = await db.messages.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", 1).to_list(2000)

    # Build a context block: include past turns as part of system prompt extension
    history_text_parts = []
    for m in history_msgs[:-1]:  # exclude the just-saved user message (we'll send it as the user msg)
        if m["role"] == "user":
            history_text_parts.append(f"[Usuario anterior]: {m['content']}")
        else:
            history_text_parts.append(f"[Tutor anterior]: {m['content']}")
    history_block = "\n\n".join(history_text_parts)

    system_message = TUTOR_SYSTEM_PROMPT
    if history_block:
        system_message = TUTOR_SYSTEM_PROMPT + "\n\nHistorial de la conversación hasta ahora:\n" + history_block

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_message,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    try:
        response_text = await chat.send_message(UserMessage(text=user_text))
    except Exception as e:
        logger.exception("LLM error")
        raise HTTPException(status_code=500, detail=f"Error del modelo: {str(e)}")

    assistant_msg = Message(session_id=session_id, role="assistant", content=str(response_text))
    await db.messages.insert_one(assistant_msg.model_dump())

    # Update session: title from first user msg, and updated_at
    new_title = session.get("title", "Nueva sesión")
    if new_title == "Nueva sesión":
        new_title = user_text[:60] + ("…" if len(user_text) > 60 else "")
    now = datetime.now(timezone.utc).isoformat()
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {"title": new_title, "updated_at": now}},
    )
    updated_session = await db.sessions.find_one({"id": session_id}, {"_id": 0})

    return SendMessageResponse(
        user_message=user_msg,
        assistant_message=assistant_msg,
        session=Session(**updated_session),
    )


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
