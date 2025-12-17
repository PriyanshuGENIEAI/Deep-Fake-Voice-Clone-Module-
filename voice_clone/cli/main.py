import argparse
from voice_clone.core.tts_engine import TTSEngine
from voice_clone.web.app import create_interface

def main():
    """
    Defines the command-line interface for the voice-clone tool.

    This function sets up two main sub-commands:
    - 'run': For generating speech from the command line.
    - 'web': For launching the interactive Gradio web interface.
    """
    parser = argparse.ArgumentParser(
        description="A command-line tool for voice cloning using AI.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-v", "--version", action="version", version="%(prog)s 1.0.0")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-command help")

    # Sub-parser for the 'run' command
    parser_run = subparsers.add_parser("run", help="Generate speech directly from the terminal.")
    parser_run.add_argument("--text", required=True, help="The text to be synthesized.")
    parser_run.add_argument("--ref", "--reference_audio", required=True, dest="reference_audio", help="Path to the reference audio file.")
    parser_run.add_argument("--out", "--output_path", default="./output.wav", dest="output_path", help="Path to save the generated audio file.")

    # Sub-parser for the 'web' command
    subparsers.add_parser("web", help="Launch the interactive Gradio web interface.")

    args = parser.parse_args()

    if args.command == "run":
        try:
            print("Initializing TTS engine...")
            tts_engine = TTSEngine()
            print(f"Synthesizing text with reference audio: {args.reference_audio}")
            output_path = tts_engine.clone_voice(args.text, args.reference_audio, args.output_path)
            print(f"\nSuccessfully generated audio file at: {output_path}")
        except Exception as e:
            print(f"\nAn error occurred: {e}")

    elif args.command == "web":
        print("Launching the Gradio web interface...")
        create_interface()

if __name__ == "__main__":
    main()
