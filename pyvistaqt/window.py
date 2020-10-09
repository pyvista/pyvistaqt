"""This module contains a Qt-compatible MainWindow class."""

from qtpy import QtCore
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """Convenience MainWindow that manages the application."""

    signal_close = Signal()
    signal_gesture = Signal(QtCore.QEvent)

    def event(self, event: QtCore.QEvent) -> bool:
        """Manage window events and filter the gesture event."""
        if event.type() == QtCore.QEvent.Gesture:  # pragma: no cover
            self.signal_gesture.emit(event)
            return True
        return super().event(event)

    def closeEvent(self, event: QtCore.QEvent) -> None:  # pylint: disable=invalid-name
        """Manage the close event."""
        self.signal_close.emit()
        event.accept()
