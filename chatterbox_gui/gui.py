from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import asdict
from typing import Optional

from .qt_compat import QtCore, QtGui, QtWidgets, QtMultimedia
Signal = getattr(QtCore, "pyqtSignal", getattr(QtCore, "Signal", None))

from chatterbox_server.tts_service import TTSService, TTSSettings
from .recorder import MicRecorder


class GenerationWorker(QtCore.QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        service: TTSService,
        text: str,
        prompt_path: Optional[str],
        output_path: str,
        settings: TTSSettings,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.text = text
        self.prompt_path = prompt_path
        self.output_path = output_path
        self.settings = settings

    def run(self) -> None:
        try:
            # progress hooks could be integrated from service if available
            self.service.synthesize_to_file(self.text, self.prompt_path, self.output_path, self.settings)
            self.progress.emit(100)
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))


class ChatterboxWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Chatterbox TTS Studio")
        self.resize(980, 640)

        # Service
        self.service = TTSService()

        # Central widget & layout
        cw = QtWidgets.QWidget(self)
        self.setCentralWidget(cw)
        main = QtWidgets.QVBoxLayout(cw)

        # Prompt controls
        prompt_group = QtWidgets.QGroupBox("Voice Prompt")
        pg_layout = QtWidgets.QGridLayout(prompt_group)
        self.prompt_path_edit = QtWidgets.QLineEdit()
        self.prompt_browse_btn = QtWidgets.QPushButton("Browse…")
        self.record_btn = QtWidgets.QPushButton("Record")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.record_status = QtWidgets.QLabel("Idle")
        pg_layout.addWidget(QtWidgets.QLabel("Prompt file (wav/mp3):"), 0, 0)
        pg_layout.addWidget(self.prompt_path_edit, 0, 1)
        pg_layout.addWidget(self.prompt_browse_btn, 0, 2)
        pg_layout.addWidget(self.record_btn, 1, 1)
        pg_layout.addWidget(self.stop_btn, 1, 2)
        pg_layout.addWidget(self.record_status, 1, 0)

        # Text input
        text_group = QtWidgets.QGroupBox("Synthesis Text")
        tg_layout = QtWidgets.QVBoxLayout(text_group)
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setPlaceholderText("Type your text here…")
        tg_layout.addWidget(self.text_edit)

        # Parameters
        params_group = QtWidgets.QGroupBox("Parameters")
        grid = QtWidgets.QGridLayout(params_group)
        self.fast_mode_cb = QtWidgets.QCheckBox("Fast mode")
        self.fast_mode_cb.setChecked(True)

        self.exag_spin = QtWidgets.QDoubleSpinBox()
        self.exag_spin.setRange(0.5, 2.0)
        self.exag_spin.setSingleStep(0.05)
        self.exag_spin.setValue(0.8)

        self.cfg_spin = QtWidgets.QDoubleSpinBox()
        self.cfg_spin.setRange(0.0, 1.0)
        self.cfg_spin.setSingleStep(0.05)
        self.cfg_spin.setValue(0.15)

        self.trim_spin = QtWidgets.QDoubleSpinBox()
        self.trim_spin.setRange(0.5, 8.0)
        self.trim_spin.setSingleStep(0.5)
        self.trim_spin.setValue(2.0)

        self.streaming_cb = QtWidgets.QCheckBox("Stream chunks")
        self.streaming_cb.setChecked(True)

        self.fade_spin = QtWidgets.QSpinBox()
        self.fade_spin.setRange(0, 200)
        self.fade_spin.setValue(30)

        self.pitch_spin = QtWidgets.QDoubleSpinBox()
        self.pitch_spin.setRange(-12.0, 12.0)
        self.pitch_spin.setSingleStep(0.5)
        self.pitch_spin.setValue(0.0)

        self.tempo_spin = QtWidgets.QDoubleSpinBox()
        self.tempo_spin.setRange(0.5, 2.0)
        self.tempo_spin.setSingleStep(0.05)
        self.tempo_spin.setValue(1.0)

        r = 0
        grid.addWidget(self.fast_mode_cb, r, 0)
        r += 1
        grid.addWidget(QtWidgets.QLabel("Exaggeration"), r, 0); grid.addWidget(self.exag_spin, r, 1); r += 1
        grid.addWidget(QtWidgets.QLabel("CFG weight"), r, 0); grid.addWidget(self.cfg_spin, r, 1); r += 1
        grid.addWidget(QtWidgets.QLabel("Prompt trim (s)"), r, 0); grid.addWidget(self.trim_spin, r, 1); r += 1
        grid.addWidget(self.streaming_cb, r, 0); r += 1
        grid.addWidget(QtWidgets.QLabel("Fade (ms)"), r, 0); grid.addWidget(self.fade_spin, r, 1); r += 1
        grid.addWidget(QtWidgets.QLabel("Pitch (semitones)"), r, 0); grid.addWidget(self.pitch_spin, r, 1); r += 1
        grid.addWidget(QtWidgets.QLabel("Tempo (x)"), r, 0); grid.addWidget(self.tempo_spin, r, 1); r += 1

        # Output controls
        out_group = QtWidgets.QGroupBox("Output")
        og = QtWidgets.QGridLayout(out_group)
        self.output_edit = QtWidgets.QLineEdit()
        self.output_browse_btn = QtWidgets.QPushButton("Choose…")
        self.generate_btn = QtWidgets.QPushButton("Generate")
        self.play_btn = QtWidgets.QPushButton("Play")
        self.play_btn.setEnabled(False)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        og.addWidget(QtWidgets.QLabel("Output wav"), 0, 0)
        og.addWidget(self.output_edit, 0, 1)
        og.addWidget(self.output_browse_btn, 0, 2)
        og.addWidget(self.generate_btn, 1, 1)
        og.addWidget(self.play_btn, 1, 2)
        og.addWidget(self.progress, 2, 0, 1, 3)

        main.addWidget(prompt_group)
        main.addWidget(text_group)
        main.addWidget(params_group)
        main.addWidget(out_group)

        # Recorder
        self.recorder = MicRecorder(self)
        self.recorder.started.connect(lambda: self.record_status.setText("Recording…"))
        self.recorder.stopped.connect(self._on_record_stopped)
        self.recorder.error.connect(lambda m: self._msg("Record error", m))
        self.recorder.duration_ms_changed.connect(self._on_record_duration)

        # Player
        self.player = QtMultimedia.QMediaPlayer(self)
        self.audio_out = QtMultimedia.QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)

        # Wire up
        self.prompt_browse_btn.clicked.connect(self._browse_prompt)
        self.output_browse_btn.clicked.connect(self._browse_output)
        self.record_btn.clicked.connect(self._start_record)
        self.stop_btn.clicked.connect(self._stop_record)
        self.generate_btn.clicked.connect(self._start_generate)
        self.play_btn.clicked.connect(self._play_output)

        # Defaults
        self.output_edit.setText(os.path.join(tempfile.gettempdir(), "chatterbox_out.wav"))

    def _msg(self, title: str, text: str) -> None:
        QtWidgets.QMessageBox.information(self, title, text)

    def _browse_prompt(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose prompt", "", "Audio (*.wav *.mp3)")
        if fn:
            self.prompt_path_edit.setText(fn)

    def _browse_output(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save output", self.output_edit.text() or "output.wav", "WAV (*.wav)")
        if fn:
            if not fn.lower().endswith(".wav"):
                fn = fn + ".wav"
            self.output_edit.setText(fn)

    def _start_record(self) -> None:
        default_name = os.path.join(tempfile.gettempdir(), "prompt.wav")
        fn, sel = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Record to",
            default_name,
            "Audio (*.wav *.mp3)"
        )
        if not fn:
            return
        if not (fn.lower().endswith(".wav") or fn.lower().endswith(".mp3")):
            fn = fn + ".wav"
        self.record_target_path = fn
        # record to temp wav; convert if mp3 requested
        self.record_temp_path = os.path.join(tempfile.gettempdir(), "_rec_tmp_prompt.wav")
        self.prompt_path_edit.setText(fn)
        self.record_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.recorder.start(self.record_temp_path)

    def _stop_record(self) -> None:
        self.recorder.stop()
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_record_stopped(self, path: str) -> None:
        target = getattr(self, "record_target_path", None)
        if not target:
            target = path
        try:
            if target.lower().endswith(".mp3"):
                import torchaudio as ta
                wav, sr = ta.load(path)
                ta.save(target, wav, sr)
            else:
                # move temp wav to target
                try:
                    if os.path.abspath(path) != os.path.abspath(target):
                        import shutil
                        shutil.move(path, target)
                    else:
                        pass
                except Exception:
                    pass
        except Exception as e:
            self._msg("Convert error", f"Saved wav, but mp3 conversion failed: {e}")
            target = path
        self.record_status.setText(f"Saved: {os.path.basename(target)}")

    def _on_record_duration(self, ms: int) -> None:
        self.record_status.setText(f"Recording… {ms/1000.0:.1f}s")

    def _collect_settings(self) -> TTSSettings:
        s = TTSSettings(
            fast_mode=self.fast_mode_cb.isChecked(),
            exaggeration=float(self.exag_spin.value()),
            cfg_weight=float(self.cfg_spin.value()),
            prompt_trim_seconds=float(self.trim_spin.value()),
            streaming=self.streaming_cb.isChecked(),
            fade_ms=int(self.fade_spin.value()),
            pitch_semitones=float(self.pitch_spin.value()),
            time_stretch=float(self.tempo_spin.value()),
        )
        # presets from fast mode
        if s.fast_mode:
            s.exaggeration = 0.8
            s.cfg_weight = 0.15
            s.prompt_trim_seconds = max(1.5, min(3.0, s.prompt_trim_seconds))
        else:
            s.exaggeration = max(0.9, s.exaggeration)
            s.cfg_weight = max(s.cfg_weight, 0.2)
            s.prompt_trim_seconds = max(3.0, s.prompt_trim_seconds)
        return s

    def _start_generate(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            self._msg("Missing text", "Please enter some text to synthesize.")
            return
        out = self.output_edit.text().strip()
        if not out:
            self._msg("Missing output", "Please choose an output path.")
            return
        prompt = self.prompt_path_edit.text().strip() or None
        settings = self._collect_settings()

        self.progress.setValue(5)
        self.generate_btn.setEnabled(False)
        self.worker = GenerationWorker(self.service, text, prompt, out, settings, self)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_generated)
        self.worker.error.connect(lambda m: self._on_error(m))
        self.worker.start()

    def _on_generated(self, path: str) -> None:
        self.progress.setValue(100)
        self.generate_btn.setEnabled(True)
        self.play_btn.setEnabled(True)
        self._msg("Done", f"Saved: {path}")

    def _on_error(self, msg: str) -> None:
        self.generate_btn.setEnabled(True)
        self._msg("Error", msg)

    def _play_output(self) -> None:
        path = self.output_edit.text().strip()
        if not path or not os.path.exists(path):
            self._msg("No output", "Generate audio first.")
            return
        url = QtCore.QUrl.fromLocalFile(path)
        self.player.setSource(url)
        self.audio_out.setVolume(0.9)
        self.player.play()


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    w = ChatterboxWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
