# Personal Voice Assistant

A voice assistant application for experimenting with state-of-the-art transcription and response generation models. This project uses [Faster Whisper](https://github.com/guillaumekln/faster-whisper) for transcription and a local LLM via [Ollama](https://ollama.com/) for generating responses.

---

## Getting Started

### Prerequisites

- **Python 3.10**
- An NVIDIA GPU with a compatible CUDA version (optional, for GPU acceleration).
- [Ollama](https://ollama.com/) installed and running. You'll also need to have a model pulled, for example:
  ```bash
  ollama run gemma3:1b
  ```

### Setup Instructions

1.  **Clone the repository and navigate to the project directory.**

2.  **Create and activate a Python virtual environment:**

    ```bash
    # Create the virtual environment
    python -m venv .venv

    # Activate the environment
    # On Windows:
    .venv\Scripts\activate
    # On macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r conversation-engine/requirements.txt
    ```

### Important: Installing PyTorch for GPU Support

By default, `pip` will install a CPU-only version of PyTorch. If you have a compatible NVIDIA GPU, you can get a significant performance boost for transcription by following these steps:

1.  **Uninstall the default version of PyTorch:**
    ```bash
    pip uninstall torch
    ```
2.  **Install the CUDA-enabled version:**
    - Go to the [PyTorch website](https://pytorch.org/get-started/locally/).
    - Select the options that match your system (e.g., `Windows`, `Pip`, your version of `CUDA`).
    - Run the generated command. It will look something like this:
    ```bash
    # This is an example for CUDA 12.1. Use the command from the website.
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```

### MeloTTS Setup

The Text-to-Speech model, MeloTTS, requires an additional setup step to download necessary resources.

1.  **Download NLTK Data:**
    After installing the requirements, run the following Python code to download the `averaged_perceptron_tagger_eng` for NLTK, which is used for English part-of-speech tagging.
    ```python
    import nltk
    nltk.download('averaged_perceptron_tagger_eng')
    ```
    You can do this in a Python interpreter or by saving the code to a file and running it.

---

## How to Run

After completing the setup and ensuring Ollama is running, start the voice assistant:

```bash
python main.py
```

The application will use your default microphone. Speak, and the assistant will respond after you stop talking. To exit, press `Ctrl+C`.
