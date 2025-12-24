from __future__ import annotations

import wave
from typing import Optional

from .qt_compat import QtCore, QtMultimedia
Signal = getattr(QtCore, "pyqtSignal", getattr(QtCore, "Signal", None))


class MicRecorder(QtCore.QObject):
    started = Signal()
    stopped = Signal(str)
    error = Signal(str)
    duration_ms_changed = Signal(int)

    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self.audio = None  # type: Optional[QtMultimedia.QAudioSource]
        self.io = None  # type: Optional[QtCore.QIODevice]
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._pull)
        self.wave: Optional[wave.Wave_write] = None
        self.output_path: Optional[str] = None
        self.bytes_written = 0
        self.sample_rate = 16000
        self.channels = 1
        self.sample_width = 2  # 16-bit
        self._duration_ms = 0

    def _setup(self):
        format = QtMultimedia.QAudioFormat()
        format.setSampleRate(self.sample_rate)
        format.setChannelCount(self.channels)
        format.setSampleFormat(QtMultimedia.QAudioFormat.SampleFormat.Int16)
        self.audio = QtMultimedia.QAudioSource(format, self)

    def start(self, output_path: str):
        try:
            self.stop()
            self._setup()
            self.output_path = output_path
            self.wave = wave.open(self.output_path, "wb")
            self.wave.setnchannels(self.channels)
            self.wave.setsampwidth(self.sample_width)
            self.wave.setframerate(self.sample_rate)
            assert self.audio is not None
            self.io = self.audio.start()
            self.timer.start(20)
            self.bytes_written = 0
            self._duration_ms = 0
            self.started.emit()
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        try:
            if self.timer.isActive():
                self.timer.stop()
            if self.audio is not None:
                self.audio.stop()
                self.audio.deleteLater()
                self.audio = None
            if self.wave is not None:
                try:
                    self.wave.close()
                except Exception:
                    pass
                self.wave = None
            if self.io is not None:
                self.io.close()
                self.io = None
            if self.output_path:
                self.stopped.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.output_path = None
            self.bytes_written = 0

    def _pull(self):
        if not self.io or not self.wave:
            return
        bytes_available = self.io.bytesAvailable()
        if bytes_available <= 0:
            return
        data = self.io.read(bytes_available)
        if data:
            self.wave.writeframes(data)
            self.bytes_written += len(data)
            # duration = bytes / (sr * channels * bytes_per_sample)
            if self.sample_rate > 0:
                self._duration_ms = int(1000 * self.bytes_written / (self.sample_rate * self.channels * self.sample_width))
                self.duration_ms_changed.emit(self._duration_ms)
