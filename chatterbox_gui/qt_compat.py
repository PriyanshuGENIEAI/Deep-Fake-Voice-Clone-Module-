# Compatibility layer to allow either PyQt6 or PySide6.
# It exposes QtCore, QtGui, QtWidgets, QtMultimedia with identical names.

try:
    from PyQt6 import QtCore, QtGui, QtWidgets, QtMultimedia  # type: ignore
    BACKEND = "PyQt6"
except Exception:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets, QtMultimedia  # type: ignore
        BACKEND = "PySide6"
        # Alias PySide6 signal/slot names to PyQt-style for compatibility
        if not hasattr(QtCore, "pyqtSignal") and hasattr(QtCore, "Signal"):
            QtCore.pyqtSignal = QtCore.Signal  # type: ignore[attr-defined]
        if not hasattr(QtCore, "pyqtSlot") and hasattr(QtCore, "Slot"):
            QtCore.pyqtSlot = QtCore.Slot  # type: ignore[attr-defined]
    except Exception as e:
        raise ImportError(
            "Neither PyQt6 nor PySide6 could be imported. Install one of them: \n"
            "  pip install 'PyQt6==6.5.3' 'PyQt6-Qt6==6.5.3' 'PyQt6-sip==13.5.1'\n"
            "or\n"
            "  pip install 'PySide6==6.5.3'\n"
            f"Original error: {e}"
        )
