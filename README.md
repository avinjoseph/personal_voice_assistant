## Team Members
1. Avin Joseph
2. Nevin Sunny
3. Ben Reji
4. Abhirami Anilkumar Shiva
5. Elizabeth Joseph


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

Before launching the application, you need to set up the model cache directories and ensure the Ollama LLM is available.

#### a. Create Cache Directories

First, run the `model_puller.sh` script to create the necessary cache directories on your host machine.

```bash
# On Linux or macOS
bash model_puller.sh

# On Windows (using Git Bash or WSL)
sh model_puller.sh
```

This script will:
1.  Create the `model_cache` directory and its subdirectories (`ollama`, `huggingface`, `nltk`).

#### b. Pull Ollama Model (gemma:2b)

The `gemma:2b` model for Ollama needs to be pulled into the running Ollama container.

# Check if the model is listed                                                                          │

```bash
docker exec -it ollama ollama list
```
If Not, then

First, ensure your `ollama` service is running:

```bash
docker-compose -f docker-compose-services.yml -f docker-compose-web.yml up -d ollama
```

Once the `ollama` container is up, pull the `gemma:2b` model:

```bash
docker exec -it ollama ollama pull gemma:2b
```

You can verify the model has been pulled successfully by listing available models:
```bash
docker exec -it ollama ollama list
```

The other models (Whisper and TTS) will be downloaded automatically by their services on the first run and stored in the `model_cache` directory.

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
