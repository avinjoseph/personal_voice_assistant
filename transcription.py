import os
import tempfile
from fastapi import FastAPI, UploadFile, File
from faster_whisper import WhisperModel
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- Model Configuration ---
# You can change the model size. Options: "tiny", "tiny.en", "base", "base.en", 
# "small", "small.en", "medium", "medium.en", "large-v1", "large-v2", "large-v3".
MODEL_SIZE = "base.en"

# You can also change the device to "cuda" for GPU acceleration,
# and compute_type to "float16" for better performance on GPU.
# For CPU, "int8" is a good option.
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
# --- End of Configuration ---


logger.info(f"Loading model '{MODEL_SIZE}' on device '{DEVICE}' with compute type '{COMPUTE_TYPE}'...")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
logger.info("Model loaded successfully.")


@app.post("/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Transcribes an audio file using the faster-whisper model.
    """
    if not audio_file:
        return {"error": "No audio file provided."}

    logger.info(f"Received file: {audio_file.filename}")

    # Save the uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
        tmp.write(await audio_file.read())
        tmp_path = tmp.name
    
    logger.info(f"Temporary file created at: {tmp_path}")

    try:
        logger.info("Starting transcription...")
        segments, info = model.transcribe(tmp_path, beam_size=5)
        
        # The transcription is a generator, so we need to iterate over it
        transcription_parts = [segment.text for segment in segments]
        full_transcription = "".join(transcription_parts).strip()
        
        logger.info(f"Transcription successful. Language: {info.language}")

        return {"transcription": full_transcription}
    except Exception as e:
        logger.error(f"An error occurred during transcription: {e}")
        return {"error": str(e)}
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
            logger.info(f"Temporary file {tmp_path} deleted.")

@app.get("/")
def read_root():
    return {"message": "Whisper transcription server is running. POST an audio file to /transcribe."}


if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
