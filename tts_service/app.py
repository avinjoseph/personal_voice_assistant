from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from melo.api import TTS
import os
import tempfile
import nltk
nltk.download('averaged_perceptron_tagger_eng')
app = FastAPI()

# Load Model
device = os.getenv("DEVICE", "cpu")
print(f"Loading MeloTTS on {device}...")
model = TTS(language="EN", device=device)
speaker_ids = model.hps.data.spk2id
default_speaker_id = list(speaker_ids.values())[0]
print("MeloTTS Loaded.")

class TTSRequest(BaseModel):
    text: str

@app.post("/synthesize")
def synthesize(req: TTSRequest):
    tmp_path = "output.wav"
    # Generate audio
    model.tts_to_file(req.text, default_speaker_id, tmp_path)

    with open(tmp_path, "rb") as f:
        audio_data = f.read()

    return Response(content=audio_data, media_type="audio/wav")