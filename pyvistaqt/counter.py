"""This module contains a basic Qt-compatible counter class."""

from qtpy.QtCore import QObject, Signal, Slot


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
            raise TypeError(
                "Expected type of `count` to be `int` but got: {}".format(type(count))
            )
        else:
            raise ValueError("count is not strictly positive.")

    @Slot()
    def decrease(self) -> None:
        """Decrease the count."""
        self.count -= 1
        if self.count <= 0:
            self.signal_finished.emit()
