# Personal Voice Assistant

A microservices-based voice assistant application that uses state-of-the-art models for transcription, response generation, and speech synthesis.

## Architecture

This project is composed of several containerized services that work together:

-   **UI (`ui`)**: A Streamlit-based web interface to interact with the assistant.
-   **Orchestrator (`orchestrator`)**: The central "brain" of the application. It receives transcribed text, calls the LLM for a response, and coordinates with other services.
-   **Whisper Service (`whisper-service`)**: A dedicated service for highly accurate speech-to-text transcription using Faster Whisper.
-   **TTS Service (`tts-service`)**: A service for converting the assistant's text responses back into speech using MeloTTS.
-   **Ollama (`ollama`)**: Hosts the local Large Language Model (e.g., Gemma 2B) that generates intelligent responses.

---

## Prerequisites

-   **Docker and Docker Compose**: To run the containerized application.
-   **Git**: To clone the repository.
-   **(Recommended) NVIDIA GPU**: For significantly faster model inference. You must have the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed.

---

## 🚀 Getting Started

Follow these steps to set up and run the voice assistant on your local machine.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd personal-voice-assistant
```

### 2. Configure Your Environment

Create a file named `.env` in the root of the project. This file will hold your local configuration.

```bash
# .env
TEAM_CALENDAR_ID=your_calendar_id_here
DEVICE=cuda
```

**Variable Reference:**
-   `TEAM_CALENDAR_ID`: An identifier for the calendar tool (you can leave the default if unsure).
-   `DEVICE`: Set to `cuda` to use an NVIDIA GPU or `cpu` to run on the CPU. Note that CPU mode will be very slow.

### 3. Download the AI Models

Before launching the application, you need to download the Ollama LLM into the shared model cache. A helper script is provided for this.

```bash
# On Linux or macOS
bash model_puller.sh

# On Windows (using Git Bash or WSL)
sh model_puller.sh
```

This script will:
1.  Create the `model_cache` directory.
2.  Run a temporary Docker container to download the `gemma:2b` model.

The other models (Whisper and TTS) will be downloaded automatically by their services on the first run and stored in the `model_cache` directory.

### 4. Launch the Application

With the configuration in place and the base model downloaded, you can start all the services using Docker Compose.

```bash
docker-compose -f docker-compose-services.yml -f docker-compose-web.yml up -d --build
```

This command will:
-   Pull the pre-built images for the services from Docker Hub.
-   Start all services in detached mode (`-d`).
-   `--build` ensures that any local changes to Dockerfiles are applied if you switch from `image` to `build` directives.

### 5. Access the Voice Assistant

Once the containers are running, you can access the web interface by navigating to:

**`http://localhost:8501`**

### 6. Stopping the Application

To stop all running services, use the following command:

```bash
docker-compose -f docker-compose-services.yml -f docker-compose-web.yml down
```

---

## Development Notes

The services are configured in `docker-compose-services.yml` to use pre-built images from Docker Hub (e.g., `image: avin5644/voice-assistant-orchestrator:v1`).

If you want to modify the source code of a service, you would need to:
1.  Comment out the `image` line for that service.
2.  Uncomment or add a `build: ./<service-directory>` line.
3.  Re-run the `docker-compose up` command to build the image from your local source code.