from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class Counter(QObject):
    """Counter augmented with a Qt timer."""

    signal_finished = pyqtSignal()

    def __init__(self, count):
        """Initialize the counter."""
        super(Counter, self).__init__()
        if isinstance(count, int) and count > 0:
            self.count = count
        elif count > 0:
            raise TypeError(
                "Expected type of `count` to be `int` but got: {}".format(type(count))
            )
        else:
            raise ValueError("count is not strictly positive.")

    @pyqtSlot()
    def decrease(self):
        """Decrease the count."""
        self.count -= 1
        if self.count <= 0:
            self.signal_finished.emit()
