from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Convenience MainWindow that manages the application."""

    signal_close = pyqtSignal()
    signal_gesture = pyqtSignal(QtCore.QEvent)

    def event(self, event):
        if event.type() == QtCore.QEvent.Gesture:
            self.signal_gesture.emit(event)
            return True
        return super().event(event)

    def closeEvent(self, event):
        """Manage the close event."""
        self.signal_close.emit()
        event.accept()
