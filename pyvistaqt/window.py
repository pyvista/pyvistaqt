"""This module contains a Qt-compatible MainWindow class."""  # noqa: D404

from __future__ import annotations

from typing import Optional

from qtpy import QtCore
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMainWindow
from qtpy.QtWidgets import QWidget


class MainWindow(QMainWindow):
    """Convenience MainWindow that manages the application."""

    signal_close = Signal()
    signal_gesture = Signal(QtCore.QEvent)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None,
        size: Optional[tuple[int, int]] = None,
    ) -> None:
        """Initialize the main window."""
        QMainWindow.__init__(self, parent=parent)
        if title is not None:
            self.setWindowTitle(title)
        if size is not None:
            self.resize(*size)

    def event(self, event: QtCore.QEvent) -> bool:
        """Manage window events and filter the gesture event."""
        if event.type() == QtCore.QEvent.Gesture:  # pragma: no cover
            self.signal_gesture.emit(event)
            return True
        return super().event(event)

    def closeEvent(self, event: QtCore.QEvent) -> None:  # pylint: disable=invalid-name  # noqa: N802
        """Manage the close event."""
        self.signal_close.emit()
        event.accept()
