# Deep-Fake-Voice-Clone-Module 🔊

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)

A simple and powerful tool to clone voices using AI, built with Coqui TTS and Gradio.

## Features

- **🎙️ High-Quality Voice Cloning:** Generate realistic speech from just a few seconds of reference audio.
- **🚀 GPU Accelerated:** Automatically uses CUDA for fast inference if a compatible GPU is detected.
- **🌐 Interactive Web UI:** A user-friendly Gradio interface for easy experimentation.
- **� Packaged for Distribution:** A proper Python package that can be installed via pip.
- **⌨️ Command-Line Interface:** A CLI for running voice cloning and launching the web app.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/voice-clone.git
    cd voice-clone
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the package in editable mode:**
    This will install the necessary dependencies from `requirements.txt`.
    ```bash
    pip install -e .
    ```

## Usage

### Web Interface

To launch the Gradio web interface, run the following command in your terminal:

```bash
voice-clone web
```

Then, open your web browser and navigate to the local URL provided (usually `http://127.0.0.1:7860`).

### Command-Line Interface

You can also run the voice cloning process directly from the command line.

```bash
voice-clone run --text "This is a test of the voice cloning system." --ref ./audio/sample.wav --out ./generated_speech.wav
```

**Arguments:**

*   `--text`: The text you want the cloned voice to say.
*   `--ref`: The path to the reference audio file (a clear, 5-10 second sample is recommended).
*   `--out`: The path to save the generated audio file.

## Project Structure

```
voice-clone/
├── voice_clone/
│   ├── __init__.py           # Package initializer
│   ├── core/                 # Core logic
│   │   ├── __init__.py
│   │   └── tts_engine.py     # Main TTS engine
│   ├── web/                  # Web interface
│   │   ├── __init__.py
│   │   └── app.py            # Gradio web application
│   └── cli/                  # Command-line interface
│       ├── __init__.py
│       └── main.py           # CLI implementation
├── tests/                    # Unit and integration tests
├── audio/                    # Example audio files
├── requirements.txt          # Project dependencies
├── setup.py                  # Package setup script
└── README.md                 # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgments

*   **[Coqui TTS](https://github.com/coqui-ai/TTS):** The powerful text-to-speech library that powers this project.
*   **[Gradio](https://www.gradio.app/):** For making it easy to create a beautiful and interactive web UI.
