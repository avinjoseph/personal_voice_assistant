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

-   **Docker Desktop**: Install Docker Desktop for windows or mac
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

Env file is already present in the repository if wanted.
Create a file named `.env` in the root of the project. This file will hold your local configuration.

```bash
# .env
TEAM_CALENDAR_ID=your_calendar_id_here
DEVICE=cpu # or DEVICE=gpu
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

The application is split into two parts: backend services and the web UI, which can be managed separately. It's recommended to start the backend services first.

#### Launching Backend Services
These services include the orchestrator, transcription, text-to-speech, and the LLM.

**(Recommended)  To Build the backend services seperately for low system with low specification. Commands are in the Development Notes**

```bash
docker-compose -f docker-compose-services.yml up -d --build
```

#### Verify Ollama Model (Optional)
After starting the backend, you can verify that the `gemma:2b` model is available.
```bash
# Check if the model is listed
docker exec -it ollama ollama list

# If gemma:2b is not in the list, pull it manually:
docker exec -it ollama ollama pull gemma:2b
```

#### Launching the Web UI
This service runs the Streamlit user interface.

```bash
docker-compose -f docker-compose-web.yml up -d --build
```

### 5. Access the Voice Assistant

Once the containers are running, you can access the web interface by navigating to:

**`http://localhost:8501`**

### 6. Stopping the Application

You can stop the services and the UI separately, which is useful for development.

```bash
# To stop all backend services
docker-compose -f docker-compose-services.yml down

# To stop the web UI
docker-compose -f docker-compose-web.yml down
```

---

## Development Notes

The services are configured in the `docker-compose` files to use pre-built images from Docker Hub (e.g., `image: avin5644/voice-assistant-orchestrator:v1`).

If you want to modify the source code of a service, you would need to:
1.  Comment out the `image` line for that service in its `docker-compose-*.yml` file.
2.  Uncomment or add a `build: ./<service-directory>` line.
3.  Re-run the appropriate `up` command to build the image from your local source code.

---

## Advanced Docker Commands

### Managing Backend Services (`orchestrator`, `whisper-service`, `tts-service`, `ollama`)

-   **Build & Run a specific service:**
    ```bash
    docker-compose -f docker-compose-services.yml up -d --build <service_name>
    # Example:
    docker-compose -f docker-compose-services.yml up -d --build orchestrator
    ```
-   **Stop a specific service:**
    ```bash
    docker-compose -f docker-compose-services.yml stop <service_name>
    ```
-   **View logs:**
    ```bash
    docker-compose -f docker-compose-services.yml logs -f <service_name>
    ```

### Managing the Web UI (`ui`)

-   **Build & Run the UI:**
    ```bash
    docker-compose -f docker-compose-web.yml up -d --build
    ```
-   **Stop the UI:**
    ```bash
    docker-compose -f docker-compose-web.yml stop
    ```
-   **View UI logs:**
    ```bash
    docker-compose -f docker-compose-web.yml logs -f
    ```