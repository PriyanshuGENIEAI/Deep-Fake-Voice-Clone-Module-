from setuptools import setup, find_packages

setup(
    name="chatterbox-server",
    version="0.1.0",
    description="Modular TTS service and API for ChatterboxTTS",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.110,<0.115",
        "uvicorn[standard]>=0.24,<0.28",
        "torchaudio",
        "torch",
    ],
    extras_require={
        "gui": [
            "PyQt6==6.5.3",
            "PyQt6-Qt6==6.5.3",
            "PyQt6-sip==13.5.1",
        ],
        "pyside": [
            "PySide6==6.5.3",
        ],
    },
    entry_points={
        "console_scripts": [
            "chatterbox-api=chatterbox_server.api:main",
            "chatterbox-gui=chatterbox_gui.gui:main",
        ]
    },
    python_requires=">=3.9",
)
