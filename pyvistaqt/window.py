"""This module contains a Qt-compatible MainWindow class."""  # noqa: D404

import contextlib

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
        parent: QWidget | None = None,
        title: str | None = None,
        size: tuple[int, int] | None = None,
    ) -> None:
        """Initialize the main window."""
        QMainWindow.__init__(self, parent=parent)
        if title is not None:
            self.setWindowTitle(title)
        if size is not None:
            self.resize(*size)

    def event(self, event: QtCore.QEvent) -> bool:
        """Manage window events and filter the gesture event."""
        if event.type() == QtCore.QEvent.Type.Gesture:  # pragma: no cover
            self.signal_gesture.emit(event)
            return True
        return super().event(event)

    def close(self) -> bool:
        """
        Close the window, tolerating an already-deleted Qt object.

        ``BackgroundPlotter.close`` schedules this window for deferred
        deletion (``deleteLater``); a later ``close()`` -- e.g. pytest-qt
        closing registered widgets at teardown -- would then raise from the
        dead C++ object.
        """
        try:
            return super().close()
        except RuntimeError:  # C++ object already deleted (PySide/PyQt)
            return True

    def deleteLater(self) -> None:  # noqa: N802
        """Schedule deletion, tolerating an already-deleted Qt object (see close)."""
        # C++ object may already be deleted (PySide/PyQt)
        with contextlib.suppress(RuntimeError):
            super().deleteLater()

    def closeEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        """Manage the close event."""
        self.signal_close.emit()
        event.accept()
