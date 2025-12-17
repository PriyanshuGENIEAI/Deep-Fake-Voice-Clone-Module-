import gradio as gr
from voice_clone.core.tts_engine import TTSEngine

def create_interface():
    """
    Initializes and launches the Gradio web interface for voice cloning.

    This function sets up the user interface, which includes text and audio
    inputs, and connects them to the TTS engine for processing.
    """
    tts_engine = TTSEngine()

    def clone_fn(text: str, audio_path: str):
        """
        A wrapper function to handle the voice cloning process within Gradio.
        It calls the TTSEngine and manages exceptions.
        """
        try:
            return tts_engine.clone_voice(text, audio_path)
        except Exception as e:
            gr.Warning(f"Error: {e}")
            return None

    description = """
    <h3>🔊 Voice Clone AI</h3>
    <p>Generate realistic voice clones from a short audio sample. Upload a clear voice recording (5-10 seconds) and enter any text to hear it spoken in that voice.</p>
    <p><b>Note:</b> This tool is for educational and research purposes only. Use responsibly and respect privacy and consent.</p>
    """

    iface = gr.Interface(
        fn=clone_fn,
        inputs=[
            gr.Textbox(label="Text", placeholder="Type what you want the cloned voice to say..."),
            gr.Audio(type="filepath", label="Reference Voice Sample (5-10 seconds)")
        ],
        outputs=gr.Audio(type="filepath", label="Generated Speech"),
        title="Voice Clone AI",
        description=description,
        theme=gr.themes.Base(primary_hue="teal", secondary_hue="teal", neutral_hue="slate"),
        examples=[
            ["This is a demonstration of AI-generated voice cloning technology. The possibilities are endless!", "./audio/Wizard-of-Oz-Dorthy.wav"],
            ["I am not a wizard, I am a humble programmer.", "./audio/male-narrator.wav"]
        ],
        allow_flagging="never"
    )

    iface.launch()

if __name__ == "__main__":
    create_interface()
