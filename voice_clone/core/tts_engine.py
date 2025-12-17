import os
import torch
from TTS.api import TTS

class TTSEngine:
    """A wrapper for the Coqui TTS library to handle voice cloning."""

    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        """
        Initializes the TTS engine.

        This sets the required environment variable for Coqui TTS and loads the
        specified model onto the appropriate device (GPU if available).

        Args:
            model_name (str): The name of the TTS model to use.
        """
        os.environ["COQUI_TOS_AGREED"] = "1"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts = TTS(model_name).to(self.device)

    def clone_voice(self, text: str, reference_audio: str, output_path: str = "./output.wav") -> str:
        """
        Generates speech in a cloned voice from a reference audio file.

        Args:
            text (str): The text to be synthesized.
            reference_audio (str): The file path to the reference audio.
            output_path (str): The file path to save the generated audio.

        Returns:
            str: The path to the generated audio file.

        Raises:
            ValueError: If the input text is empty or only contains whitespace.
            FileNotFoundError: If the reference audio file does not exist.
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty.")

        if not os.path.exists(reference_audio):
            raise FileNotFoundError(f"Reference audio file not found at: {reference_audio}")

        self.tts.tts_to_file(
            text=text,
            speaker_wav=reference_audio,
            language="en",
            file_path=output_path
        )
        return output_path
