from fastapi import FastAPI, UploadFile, File
from faster_whisper import WhisperModel
import os
import shutil
import traceback

app = FastAPI()

# Load Model Once at Startup
model_size = "base.en"
device = os.getenv("DEVICE", "cpu")
compute_type = "float16" if device == "cuda" else "int8"

print(f"Loading Whisper ({model_size}) on {device}...")
model = WhisperModel(model_size, device=device, compute_type=compute_type)
print("Whisper Loaded.")


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    print(f"Processing file: {file.filename}")
    try:
        # Save temp file
        with open("temp.wav", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Check if file exists and has size
        file_size = os.path.getsize("temp.wav")
        print(f"File saved. Size: {file_size} bytes")
        
        if file_size == 0:
            return {"text": ""}

        print("Starting transcription...")
        segments, info = model.transcribe("temp.wav", 
                                          # A. IMPROVE ACCURACY
            beam_size=5,            # Searches 5 paths for the best sentence (higher = better accuracy, slightly slower)
            best_of=5,              # Similar to beam_size, ensures robustness
    
             # B. FORCE ENGLISH (Crucial for short commands)
            language="en",          # Prevents it from guessing the wrong language on short audio
    
            # C. REDUCE NOISE & HALLUCINATIONS
            vad_filter=True,        # Removes silence/background noise before processing
            vad_parameters=dict(min_silence_duration_ms=500), # Only cut if silence > 0.5s
    
            # D. PREVENT "CREATIVE" OUTPUT
            temperature=0.0,        # 0.0 makes the model deterministic (stick to facts, don't guess)
    
            # E. CONTEXT HINT (Helps it understand it's a command)
            initial_prompt="A user giving a voice command to an AI assistant.")
        
        print(f"Detected language '{info.language}' with probability {info.language_probability}")
        
        text = " ".join([segment.text for segment in segments]).strip()
        print(f"Transcription result: {text}")
        
        return {"text": text}

    except Exception as e:
        # --- FIX: Print the actual error ---
        error_msg = str(e)
        print(f"CRITICAL ERROR: {error_msg}")
        traceback.print_exc() # This prints the full error to docker logs
        return {"text": "", "error": error_msg}