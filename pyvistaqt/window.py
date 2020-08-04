from qtpy import QtCore
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Convenience MainWindow that manages the application."""

    signal_close = Signal()
    signal_gesture = Signal(QtCore.QEvent)

    def event(self, event):
        if event.type() == QtCore.QEvent.Gesture:
            self.signal_gesture.emit(event)
            return True
        return super().event(event)

    def closeEvent(self, event):
        """Manage the close event."""
        self.signal_close.emit()
        event.accept()
