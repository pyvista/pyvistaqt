"""This module contains a basic Qt-compatible counter class."""  # noqa: D404

from __future__ import annotations

from qtpy.QtCore import QObject
from qtpy.QtCore import Signal
from qtpy.QtCore import Slot


class Counter(QObject):
    """Counter class with Qt signal/slot."""

    # pylint: disable=too-few-public-methods

    signal_finished = Signal()

    def __init__(self, count: int) -> None:
        """Initialize the counter."""
        super().__init__()
        if isinstance(count, int) and count > 0:
            self.count = count
        elif count > 0:
            msg = f"Expected type of `count` to be `int` but got: {type(count)}"
            raise TypeError(msg)
        else:
            msg = "count is not strictly positive."
            raise ValueError(msg)

    @Slot()
    def decrease(self) -> None:
        """Decrease the count."""
        self.count -= 1
        if self.count <= 0:
            self.signal_finished.emit()
