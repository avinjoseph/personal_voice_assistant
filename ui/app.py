import streamlit as st
import requests
import os

# --- Configuration ---
st.set_page_config(page_title="Voice Assistant", page_icon="🎙️")
st.title("🎙️ Smart Voice Assistant")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

# --- Display Chat History ---
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "audio" in msg:
            # logic: Autoplay ONLY if it's the last message in the list
            is_last_message = (i == len(st.session_state.messages) - 1)
            st.audio(msg["audio"], format="audio/wav", autoplay=is_last_message)

# --- Audio Input ---
st.write("---")
audio_value = st.audio_input("Record a voice command")

# --- Processing Logic ---
if audio_value:
    # Check if this specific audio file has already been processed
    # We compare the raw bytes to ensure we don't re-run the same command on refresh
    current_audio_bytes = audio_value.getvalue()
    
    if st.session_state.last_processed_audio != current_audio_bytes:
        
        with st.status("Processing...", expanded=True) as status:
            try:
                # 1. Send to Orchestrator
                files = {"file": ("audio.wav", audio_value, "audio/wav")}
                res = requests.post(f"{ORCHESTRATOR_URL}/process", files=files)
                
                if res.status_code == 200:
                    status.update(label="Response Received!", state="complete")
                    
                    # 2. Extract Data
                    response_audio = res.content
                    ai_text = res.headers.get("X-Response-Text", "(No response text)")
                    user_text = res.headers.get("X-User-Text", "(No user text)")
                    
                    # 3. Update History
                    # Add User Message
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": user_text
                    })
                    
                    # Add Assistant Message (Text + Audio)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": ai_text,
                        "audio": response_audio
                    })
                    
                    # 4. Mark this audio as processed
                    st.session_state.last_processed_audio = current_audio_bytes
                    
                    # 5. Rerun to display messages at the top
                    st.rerun()
                    
                else:
                    status.update(label="Error", state="error")
                    st.error(f"Server Error: {res.text}")
                    
            except Exception as e:
                status.update(label="Connection Failed", state="error")
                st.error(f"Connection Failed: {e}")