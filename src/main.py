import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile
import logging
import threading
import datetime
import re
from faster_whisper import WhisperModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
import json
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from tools import get_weather, manage_calendar
import torch
import shutil, subprocess
from melo.api import TTS

# Silence third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("faster_whisper").setLevel(logging.WARNING)

# --- Configuration ---
# Whisper Model
WHISPER_MODEL_SIZE = "base.en"
# Auto-select device: use CUDA if available, otherwise CPU.
try:
    _has_cuda = torch.cuda.is_available()
except Exception:
    _has_cuda = False
    if shutil.which("nvidia-smi"):
        try:
            subprocess.check_call(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _has_cuda = True
        except Exception:
            _has_cuda = False
# _has_cuda = False

WHISPER_DEVICE = "cuda" if _has_cuda else "cpu"
# Prefer float16 on GPU for speed/accuracy tradeoff, keep int8 for CPU
WHISPER_COMPUTE_TYPE = "float16" if _has_cuda else "int8"

# MeloTTS Model
MELO_MODEL_ID = "EN-US-HCL-v2"
MELO_DEVICE = "cuda" if _has_cuda else "cpu"

# Ollama Model
OLLAMA_MODEL_NAME = "gemma3:1b" 

# Audio Recording
SAMPLE_RATE = 16000  # 16kHz
CHANNELS = 1
DTYPE = 'int16'

# Define path to the prompt file
PROMPT_FILE_PATH = os.path.join(os.path.dirname(__file__), 'system_prompt.txt')

# Voice Activity Detection (VAD)
VAD_ENERGY_THRESHOLD = 300  # Adjust this based on your microphone's sensitivity
VAD_SILENCE_DURATION = 1.5  # Seconds of silence to consider the end of speech
VAD_PRE_SPEECH_PAD = 0.8 # Seconds of audio to keep before speech starts

# --- Setup Logging ---
# Only show actual errors, hide "Listening...", "Thinking...", etc.
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

def load_system_prompt():
    try:
        with open(PROMPT_FILE_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to load system prompt: {e}")
        return "You are a helpful voice assistant. Keep your answers concise and conversational. Maximum 50 words."


def main():
    """
    Main function to run the voice-driven chat loop.
    """
    # --- 1. Initialize Models ---
    logging.info(f"Using device: {WHISPER_DEVICE} ({WHISPER_COMPUTE_TYPE}) for Whisper model.")
    logging.info("Loading models...")
    try:
        whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
        llm = ChatOllama(model=OLLAMA_MODEL_NAME)
        logging.info("Loading MeloTTS model, this may take a moment on first run...")
        melo_model = TTS(language="EN",device=MELO_DEVICE)
        
        speaker_ids = melo_model.hps.data.spk2id
        
        speaker_id = list(speaker_ids.values())[0]
        logging.info(f"Using MeloTTS speaker ID: {speaker_id}")

        logging.info("Models loaded successfully.")
    except Exception as e:
        logging.error(f"Failed to load models: {e}")
        logging.error("Please ensure Ollama is running and all model dependencies are met.")
        return

    # --- 2. Setup LangChain ---
    # prompt = ChatPromptTemplate.from_messages([
    #     ("system", "You are a helpful voice assistant. Keep your answers concise and conversational. Maximum 50 words."),
    #     ("human", "{question}")
    # ])
    system_prompt_text = load_system_prompt()
    logging.info("System prompt loaded.")
    
    chat_history = [SystemMessage(content=system_prompt_text)]
    # chain = prompt | llm | StrOutputParser()

    # --- 3. Main Conversation Loop ---
    print("\n--- Voice Assistant Ready ---")
    print("Speak into your microphone. The assistant will respond when you stop talking.")
    
    while True:
        try:
            # --- 3.1. Record Audio with VAD ---
            logging.info("Listening for speech...")
            audio_data = record_with_vad()
            
            # --- 3.2. Transcribe Audio ---
            logging.info("Transcribing audio...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", mode='w+b') as tmp_audio_file:
                wav.write(tmp_audio_file.name, SAMPLE_RATE, audio_data)
                
                segments, _ = whisper_model.transcribe(
                    tmp_audio_file.name, 
                    beam_size=5,
                    # This prompt helps the model expect these specific keywords
                    initial_prompt="A voice command to a calendar assistant. Delete the previously created appointment. Add a meeting. Check weather in Marburg."
                )
                
                transcribed_text = "".join(segment.text for segment in segments).strip()
            
            os.remove(tmp_audio_file.name) # Clean up the temporary file

            if not transcribed_text:
                logging.warning("Transcription is empty, listening again.")
                continue

            print(f"You: {transcribed_text}")

            now_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
            current_system_prompt = load_system_prompt().replace("{current_time}", now_str)
            
            # Update the specific system message at index 0, keep the rest of history!
            if len(chat_history) > 0 and isinstance(chat_history[0], SystemMessage):
                chat_history[0].content = current_system_prompt
            else:
                chat_history.insert(0, SystemMessage(content=current_system_prompt))
            
            # 2. Add User's new input
            chat_history.append(HumanMessage(content=transcribed_text))
            
            logging.info("Thinking...")
            
            # 3. Invoke LLM with FULL history
            ai_msg = llm.invoke(chat_history)
            response_text = ai_msg.content.strip()
            
            # Robust JSON extraction
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            clean_text = ""
            if json_match:
                clean_text = json_match.group(1).strip()
            
            if clean_text and clean_text.startswith("{"):
                try:
                    tool_call = json.loads(clean_text)
                    tool_name = tool_call.get("tool")
                    tool_args = tool_call.get("args", {})
                    
                    print(f"[System] Calling Tool: {tool_name} with args: {tool_args}")
                    
                    tool_result = ""
                    if tool_name == "get_weather":
                        tool_result = get_weather(tool_args.get("city"))
                    elif tool_name == "manage_calendar":
                        tool_result = manage_calendar(
                            action=tool_args.get("action"),
                            event_id=tool_args.get("event_id"),
                            title=tool_args.get("title"),
                            start_time=tool_args.get("start_time"),
                            end_time=tool_args.get("end_time"),
                            location=tool_args.get("location"),
                            description=tool_args.get("description")
                        )
                        
                    print(f"✅ Result : {tool_result}")
                        
                    # Remove the JSON from the history if we want a clean conversation, 
                    # but usually we just append the result.
                    
                    if tool_name == "get_weather":
                        tool_feedback = (
                            f"Tool Output: {str(tool_result)}\n"
                            "--- INSTRUCTION ---\n"
                            "Using the above data, answer the user's question in a single, natural spoken sentence.\n"
                            "- If the user asked for a specific day (e.g., 'Friday'), ONLY mention the weather for that day.\n"
                            "- If the user asked for the general forecast, summarize it briefly.\n"
                            "- Do NOT read the raw list or bullet points.\n"
                            "- Do NOT say 'Here is the weather' or 'The tool says'. Just give the answer."
                        )
                    elif tool_name == "manage_calendar":
                        tool_feedback = (
                            f"Tool Output: {str(tool_result)}\n"
                            "--- INSTRUCTION ---\n"
                            "Using the above data, answer the user's question in a single, natural spoken sentence.\n"
                            "- If listing events, summarize them naturally (e.g., 'You have a meeting about X on [Day] at [Time]').\n"
                            "- Do NOT read the raw JSON structure, keys like 'start_time', or IDs unless asked.\n"
                            "- If confirming an action (create/update/delete), just say it was done successfully.\n"
                            "- Keep it conversational and brief."
                        )
                    else:
                        # Fallback for unknown tools
                        tool_feedback = f"Tool Output: {str(tool_result)}. Now answer the user's original question based on this data."

                    chat_history.append(SystemMessage(content=tool_feedback))
                    
                    final_ai_msg = llm.invoke(chat_history)
                    raw_response = final_ai_msg.content
                    
                except json.JSONDecodeError:
                    logging.error(f"Failed to decode JSON from: {clean_text}")
                    raw_response = response_text # Fallback to original text if JSON was a false positive
                    
            else:
                raw_response = response_text
                
            chat_history.append(AIMessage(content=raw_response))
            
            print(f"Assistant (raw): {raw_response}")
            
            
            
            if isinstance(raw_response, dict):
                response = raw_response.get("text", "")
            else:
                response = str(raw_response)

            response = response.strip()
            print(f"Assistant: {response}")

            # --- 3.4. Convert Response to Speech ---
            logging.info("Converting response to speech...")
            tmp_speech_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp_speech_file.close()
            try:
                # Generate speech audio file
                melo_model.tts_to_file(response,speaker_id, tmp_speech_file.name)

                # Play the generated audio file
                samplerate, audio_data = wav.read(tmp_speech_file.name)
                sd.play(audio_data, samplerate)
                sd.wait()
            finally:
                # Clean up the temporary file
                if os.path.exists(tmp_speech_file.name):
                    os.remove(tmp_speech_file.name)
            
            print("-" * 50)

        except KeyboardInterrupt:
            print("\nExiting voice assistant.")
            break
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")
            break

def record_with_vad():
    """
    Records audio from the microphone using Voice Activity Detection (VAD).
    This function waits until speech is detected and then records until a period of silence.
    """
    is_speaking = False
    silent_chunks = 0
    audio_buffer = []
    pre_speech_buffer = []
    
    silence_chunks_needed = int((VAD_SILENCE_DURATION * SAMPLE_RATE) / 512)  # 512 is chunk size
    pre_speech_chunks_needed = int((VAD_PRE_SPEECH_PAD * SAMPLE_RATE) / 512)
    
    recording_finished = threading.Event()

    def callback(indata, frames, time, status):
        nonlocal is_speaking, silent_chunks, audio_buffer, pre_speech_buffer
        if status:
            logging.warning(f"Audio stream status: {status}")
        
        energy = np.linalg.norm(indata) * 10  # Simple energy calculation
        
        if is_speaking:
            audio_buffer.append(indata.copy())
            if energy < VAD_ENERGY_THRESHOLD:
                silent_chunks += 1
                if silent_chunks > silence_chunks_needed:
                    recording_finished.set()
                    raise sd.CallbackStop
            else:
                silent_chunks = 0
        else:
            pre_speech_buffer.append(indata.copy())
            if len(pre_speech_buffer) > pre_speech_chunks_needed:
                pre_speech_buffer.pop(0)

            if energy > VAD_ENERGY_THRESHOLD:
                logging.info("Speech detected.")
                is_speaking = True
                audio_buffer.extend(pre_speech_buffer)
                pre_speech_buffer.clear()
                silent_chunks = 0

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, callback=callback):
            recording_finished.wait()  # Block until the callback signals completion
    except Exception as e:
        logging.error(f"Error during audio recording: {e}")
        return np.array([], dtype=DTYPE)

    if not audio_buffer:
        logging.info("No audio recorded.")
        return np.array([], dtype=DTYPE)

    return np.concatenate(audio_buffer)


if __name__ == "__main__":
    main()
