from fastapi import APIRouter, Depends, Body, Request, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from pprint import pprint
import tempfile
import logging
import json
from typing import List, Dict, Any

from src.logic.router_chain import Router_chain
from src.logic.qa_chain import QAChain
from src.dependencies.combined_dependencies import combined_dependencies
from src.dependencies.session_dependece import update_session
from src.dependencies.messages_dependence import update_messages
from src.models.session import SessionModel
from src.schemas.tools import QAToolModel
from src.logic.form_chain import Form_chain
from src.utils.api_calls import transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter()

# ------ RUTA PARA ENVIAR AL AGENTE IA ------
@router.post("/chat")
async def chat(
    request: Request,
    context: dict = Depends(combined_dependencies),
    
) -> StreamingResponse:
    """Procesa el mensaje del usuario y genera una respuesta del chatbot"""

    # ----PROCESAMIENTO DE LA CONSULTA DEL USUARIO
     # Detectamos si la request es JSON (texto) o multipart (audio)
    content_type = request.headers.get("content-type", "")

    try:
        if "application/json" in content_type:
            # ---- MENSAJE DE TEXTO NORMAL
            user_data = await request.json()
            user_timestamp = datetime.now(timezone.utc)
            type: str = user_data["type"]
            content = user_data["content"]

        elif "multipart/form-data" in content_type:
            # ---- AUDIO MULTIPART
            form = await request.form()
            audio_file = form.get("audio")

            if not audio_file:
                raise HTTPException(status_code=400, detail="Archivo de audio no proporcionado")

            # Guardar temporalmente y transcribir
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                content = await audio_file.read()
                tmp.write(content)
                tmp_path = tmp.name

            content = await transcribe_audio(tmp_path)
            print(f"Audio transcrito: {content}")

            user_timestamp = datetime.now(timezone.utc)
            type = "text"

        else:
            raise HTTPException(status_code=415, detail="Content not suported")

    except Exception as e:
        logging.error(f"Error processing input in /chat: {e}")
        raise HTTPException(status_code=400, detail="Invalid input")

    
    # ----CONTEXTO DE LA DEPENDENCIAS
    # Es necesario que 'context.get("messages_context")' como 'context.get("tools_data")' sean diccionarios para asegurar la mutabilidad
    try:
        session: SessionModel = context.get("session_context")
        history: List[Dict[str,Any]] = context.get("messages_context")
        username = session.name
    
    except Exception as e:
            logging.error(f"Error retriving session objects in route /chat: {e}")
            raise Exception(f"Error retriving session objects in route /chat: {e}")

    # ----FUNCIÓN ASÍNCRONA GENERADORA DE RESPUESTAS
    async def response_stream():
        
        try:        
            print(f"SESSION CONTEXT 1: {session}")
            partial_answers = []
            bot_matadata = {}
            user_matadata = {}
            input = ""

            # ---- PROCESADO DE RESPUESTA CUANDO SE EXIGE LOCALIZACIÓN
            if type=="inm_localization_action":
                localization: tuple = content
                tools_data: dict = session.tools_data
                qa_tool: QAToolModel = tools_data.get("qa_tool")
                print(f"QA TOOL: {qa_tool}")
                qa_tool.inm_localization = localization
                user_matadata["type"] = type

                # Generación la respuesta del chatbot.
                async for partial_response in QAChain.direct_execute(input, qa_tool):

                    # las respuestas son diccionarios en formato {"type": type, "content": content}
                    yield json.dumps(partial_response) + "\n" # Importante el salto de línea para dividir las respuestas
                    if partial_response["type"] == "text":
                        partial_answers.append(partial_response["content"])
                    if partial_response["type"] == "metadata":
                        bot_matadata[partial_response["key"]] = partial_response["content"]

            # ---- PROCESADO DE RESPUESTA CUANDO SE PIDEN DATOS PERSONALES
            if type=="personal_form_action":
                personal_data: dict = content
                user_matadata["type"] = type

                # Generación la respuesta del chatbot.
                async for partial_response in Form_chain.execute(personal_data):

                    # las respuestas son diccionarios en formato {"type": type, "content": content}
                    yield json.dumps(partial_response) + "\n" # Importante el salto de línea para dividir las respuestas
                    if partial_response["type"] == "text":
                        partial_answers.append(partial_response["content"])
                    if partial_response["type"] == "metadata":
                        bot_matadata[partial_response["key"]] = partial_response["content"]

            # ---- PROCESADO DE RESPUESTA GENÉRICO PARA INPUT DE USUARIO
            if type=="text":
                input: str = content
                user_matadata["type"] = type
                        
                # Generación la respuesta del chatbot.
                async for partial_response in Router_chain.execute(input, session, history, username):

                    # Las respuestas son diccionarios en formato {"type": type, "content": content}
                    yield json.dumps(partial_response) + "\n" # Importante el salto de línea para dividir las respuestas
                    if partial_response["type"] == "text":
                        content_chunk = partial_response["content"]
                        partial_answers.append(content_chunk)
                    if partial_response["type"] == "metadata":
                        bot_matadata[partial_response["key"]] = partial_response["content"]
                    else:
                        pass

            print(f"BOT METADATA: {bot_matadata}")
            answer = "".join(partial_answers)        
            await update_session(session, request)
            await update_messages(user_timestamp, input, answer, user_matadata, bot_matadata, request)

        except Exception as e:
            logger.error(f"Error in /chat route: {e}")
            yield {"type": "text", "content": "Lo siento, ahora mismo no podemos atenderte."}

    return StreamingResponse(response_stream(), media_type="text/event-stream")