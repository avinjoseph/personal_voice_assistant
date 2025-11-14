# personal_voice_assistant
A voice assistant application for experimenting with state-of-the-art transcription, response generation, and text-to-speech models.

- transcription.py :- Audio trancription using Faster Whisper
    Server will be up and running in the port : http://0.0.0.0:8000
    POST REQUEST Example :- curl -X POST -F "audio_file=@D:/Jvke autumn.mp3" http://127.0.0.1:8000/transcribe