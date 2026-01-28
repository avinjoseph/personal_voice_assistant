from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
import requests
import os
import json
import re
from datetime import datetime, timedelta
from langchain_ollama import ChatOllama
from tools import get_weather, manage_calendar

app = FastAPI()

# --- CONFIGURATION ---
WHISPER_URL = os.getenv("WHISPER_URL", "http://whisper-service:8001")
TTS_URL = os.getenv("TTS_URL", "http://tts-service:8002")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

# Initialize LLM
llm = ChatOllama(model="gemma:2b", base_url=OLLAMA_URL)

@app.get("/")
def read_root():
    return {"status": "Orchestrator is running"}

@app.post("/process")
async def process_audio(file: UploadFile = File(...)):
    print(f"--- New Request: {file.filename} ---")
    
    # 1. TRANSCRIBE
    try:
        audio_bytes = await file.read()
        files = {'file': (file.filename, audio_bytes, file.content_type)}
        res_asr = requests.post(f"{WHISPER_URL}/transcribe", files=files)
        user_text = res_asr.json().get("text", "")
        print(f"User said: {user_text}")
    except Exception as e:
        print(f"Whisper Error: {e}")
        return Response(content=b"", media_type="audio/wav")

    if not user_text:
        return Response(content=b"", media_type="audio/wav")

    user_lower = user_text.lower()
    final_answer = ""
    
    # ====================================================
    # INTENT 1: WEATHER
    # ====================================================
    if "weather" in user_lower or "rain" in user_lower or "temperature" in user_lower:
        print(">> Detected Intent: WEATHER")
        
        extraction_prompt = f"Extract city name from: '{user_text}'. Return ONLY the city name. If none, return 'Frankfurt'."
        city_name = llm.invoke(extraction_prompt).content.strip().replace(".", "").replace('"', '')
        print(f"Extracted City: {city_name}")
        
        weather_data = get_weather(city_name)
        
        summary_prompt = f"Data: {weather_data}. User asked: {user_text}. Summarize the weather in 1 sentence."
        final_answer = llm.invoke(summary_prompt).content

    # ====================================================
    # INTENT 2: CALENDAR (With Safety Bypass)
    # ====================================================
    elif "appointment" in user_lower or "meeting" in user_lower or "schedule" in user_lower:
        print(">> Detected Intent: CALENDAR")
        
        # Context
        now = datetime.now()
        current_time_str = now.strftime("%Y-%m-%d %H:%M")
        tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Step A: Extraction
        extraction_prompt = f"""
        Current Date: {current_time_str}
        Tomorrow Date: {tomorrow_str}
        Request: "{user_text}"
        
        Extract parameters into JSON.
        - action: "list", "create", "delete"
        - title: string
        - start_time: YYYY-MM-DDTHH:MM
        
        Example: "Add meeting tomorrow 9am" -> {{"action": "create", "title": "Meeting", "start_time": "{tomorrow_str}T09:00"}}
        
        JSON ONLY:
        """
        
        try:
            llm_response = llm.invoke(extraction_prompt).content.strip()
            print(f"LLM Extraction: {llm_response}")
            
            json_match = re.search(r'(\{.*\})', llm_response, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group(1))
            else:
                params = {"action": "list"} 

            print(f"Executing Calendar Tool with: {params}")
            
            # Step B: Execute Tool
            tool_output = manage_calendar(**params)
            print(f"Tool Output: {tool_output}")
            
            # Step C: Summarize (With Failsafe)
            if params.get("action") == "list" and ("no appointments" in str(tool_output).lower()):
                final_answer = "You have no appointments scheduled."
            else:
                # We ask LLM to "Rephrase" not "Report"
                summary_prompt = f"""
                TEXT TO READ: "{tool_output}"
                INSTRUCTION: Read the text above to the user clearly. Do not add any extra words.
                """
                final_answer = llm.invoke(summary_prompt).content.strip()
                
                # --- THE FIX: SAFETY BYPASS ---
                # If LLM hallucinates a refusal, we overwrite it with the raw data.
                refusal_keywords = ["unable to", "cannot access", "not provided", "no information", "cannot answer"]
                if any(k in final_answer.lower() for k in refusal_keywords):
                    print("!!! LLM REFUSED TO READ DATA. USING RAW OUTPUT. !!!")
                    # Clean up the raw string slightly for TTS
                    clean_output = str(tool_output).replace("[", "").replace("]", "").replace("{", "").replace("}", "")
                    final_answer = f"Here is the information: {clean_output}"

        except Exception as e:
            print(f"Calendar Logic Error: {e}")
            final_answer = "I processed your request, but there was a system error."

    # ====================================================
    # INTENT 3: CHAT
    # ====================================================
    else:
        print(">> Detected Intent: CHAT")
        final_answer = llm.invoke(f"Reply briefly to: {user_text}").content

    print(f"Final Answer: {final_answer}")

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
         raise HTTPException(status_code=500, detail=f"TTS Error: {str(e)}")