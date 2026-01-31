from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
import requests
import os
import json
import re
import logging
from datetime import datetime
from langchain_ollama import ChatOllama
from tools import get_weather, manage_calendar, format_weather_response
# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

app = FastAPI()

# --- CONFIGURATION ---
WHISPER_URL = os.getenv("WHISPER_URL", "http://whisper-service:8001")
TTS_URL = os.getenv("TTS_URL", "http://tts-service:8002")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
llm = ChatOllama(model="gemma:2b", base_url=OLLAMA_URL)

# --- CONTEXT ---
class AssistantContext:
    def __init__(self):
        self.last_city = "Marburg"
        self.last_event_id = None

    def update_context(self, city=None, event_id=None):
        if city: self.last_city = city
        if event_id: self.last_event_id = event_id

context = AssistantContext()

def safe_extract_json(text):
    """Robustly parse JSON even with LLM filler text."""
    try:
        text = text.replace("'", '"')
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        return json.loads(match.group(1)) if match else None
    except: 
        return None

@app.post("/process")
async def process_audio(file: UploadFile = File(...)):
    logger.info(f"Processing audio file: {file.filename}")
    
    # 1. TRANSCRIBE
    try:
        audio_bytes = await file.read()
        res_asr = requests.post(f"{WHISPER_URL}/transcribe", files={'file': (file.filename, audio_bytes, file.content_type)})
        user_text = res_asr.json().get("text", "")
        logger.info(f"Transcribed Text: {user_text}")
    except Exception as e:
        logger.error(f"Whisper Error: {e}")
        return Response(content=b"", media_type="audio/wav")

    if not user_text:
        return Response(content=b"", media_type="audio/wav")

    user_lower = user_text.lower()
    final_answer = ""

    # ==========================================
    # INTENT 1: WEATHER
    # ==========================================
    # INTENT: WEATHER (Hybrid Extraction)
    if any(k in user_lower for k in ["weather", "rain", "temperature", "forecast"]):
        # Deterministic check for required project cities
        if "frankfurt" in user_lower:
            city_name = "Frankfurt"
        elif "marburg" in user_lower:
            city_name = "Marburg"
        elif "there" in user_lower or "that city" in user_lower:
            # Resolve 'there' using conversation history (Requirement 66)
            city_name = context.last_city
        else:
            # Fallback to LLM for unknown cities
            prompt = f"Extract ONLY the city name from: '{user_text}'. Return 'NONE' if no city found."
            llm_res = llm.invoke(prompt).content.strip().replace(".", "")
            city_name = llm_res if "NONE" not in llm_res.upper() else context.last_city

        # Update memory and fetch data
        context.update_context(city=city_name)
        weather_data = get_weather(city_name, user_text)
        
        # If API succeeds, return formatted response; else error
        if weather_data and not isinstance(weather_data, str):
            final_answer = format_weather_response(weather_data, user_text)
        else:
            # Fallback if tools.py returned an error string
            final_answer = str(weather_data) if weather_data else f"I couldn't find weather for {city_name}."
        # INTENT 2: CALENDAR
    # ==========================================
    # Updated Calendar Intent Logic in main.py
    elif any(k in user_lower for k in ["appointment", "meeting", "schedule", "delete", "list", "update", "change", "add", "where", "next"]):
        logger.info("Intent: CALENDAR")
        
        is_next_query = any(k in user_lower for k in ["next", "where"]) and "appointment" in user_lower
        now_str = datetime.now().strftime('%Y-%m-%dT%H:%M')
        # Provide the last known ID to the LLM to help it decide if it should use it
        prompt = f"""
        Current Date/Time: {now_str}.
        User Request: "{user_text}"
        
        Task: Extract JSON for calendar management.
        - action: "create", "list", "delete", "update"
        - title: the name of the event
        - start_time: format as YYYY-MM-DDTHH:MM (Convert "10 p.m." to 22:00)
        - location: extracted location or "TBD"
        - If the user says 'update', 'change', or 'move', action MUST be "update".
        - If the user says 'delete' or 'remove', action MUST be "delete".
        - If the user says 'add', 'create', or 'schedule', action MUST be "create".
        - If the user says 'list' or 'show', action MUST be "list".
        
        JSON ONLY: {{"action": "create|list|delete|update", "title": "string", "start_time": "string", "location": "string", "event_id": int}}
        """
        
        llm_res = llm.invoke(prompt).content
        params = safe_extract_json(llm_res) or {"action": "list"}
        logging.info(f"Parsed Calendar Params: {params}")
        
        if any(k in user_lower for k in ["update", "change", "move"]):
            params["action"] = "update"
        elif any(k in user_lower for k in ["delete", "remove"]):
            params["action"] = "delete"
        elif any(k in user_lower for k in ["list", "show", "where", "find"]):
            params["action"] = "list"
        elif any(k in user_lower for k in ["add", "create", "schedule"]):
            params["action"] = "create"
        
        
        # REQUIREMENT: Handle context for 'latest' ID when not provided (Slide 134)
        if params.get("action") in ["delete", "update", "change"] and not params.get("event_id"):
            params["event_id"] = context.last_event_id
            logger.info(f"Using context ID for {params.get('action')}: {context.last_event_id}")

        # Execute tool
        tool_output = manage_calendar(is_next_query=is_next_query, **params)
        
        # REQUIREMENT: Update context with the ID of the newly created or latest appointment
        id_match = re.search(r'ID (\d+)', str(tool_output))
        if id_match:
            context.update_context(event_id=int(id_match.group(1)))
            
        final_answer = str(tool_output)
        
      
    # INTENT 3: CHAT
    # ==========================================
    else:
        logger.info("Intent: CHAT")
        final_answer = llm.invoke(f"Reply briefly: {user_text}").content

    logger.info(f"Final Answer: {final_answer}")

    # 3. SYNTHESIZE
    try:
        res_tts = requests.post(f"{TTS_URL}/synthesize", json={"text": final_answer})
        return Response(
            content=res_tts.content, 
            media_type="audio/wav", 
            headers={
                "X-Response-Text": final_answer.replace("\n", " ").strip(), 
                "X-User-Text": user_text.replace("\n", " ").strip()
            }
        )
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        return Response(status_code=500)