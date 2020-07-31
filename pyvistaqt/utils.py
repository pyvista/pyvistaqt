from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QDoubleSpinBox,
    QSlider,
)


class DoubleSlider(QSlider):
    """Double precision slider.

    Reference:
    https://gist.github.com/dennis-tra/994a65d6165a328d4eabaadbaedac2cc

    """

    def __init__(self, *args, **kwargs):
        """Initialize the double slider."""
        super().__init__(*args, **kwargs)
        self.decimals = 5
        self._max_int = 10 ** self.decimals

        super().setMinimum(0)
        super().setMaximum(self._max_int)

        self._min_value = 0.0
        self._max_value = 20.0

    @property
    def _value_range(self):
        """Return the value range of the slider."""
        return self._max_value - self._min_value

    def value(self):
        """Return the value of the slider."""
        return (
            float(super().value()) / self._max_int * self._value_range + self._min_value
        )

    def setValue(self, value):
        """Set the value of the slider."""
        super().setValue(
            int((value - self._min_value) / self._value_range * self._max_int)
        )

    def setMinimum(self, value):
        """Set the minimum value of the slider."""
        if value > self._max_value:  # pragma: no cover
            raise ValueError("Minimum limit cannot be higher than maximum")

        self._min_value = value
        self.setValue(self.value())

    def setMaximum(self, value):
        """Set the maximum value of the slider."""
        if value < self._min_value:  # pragma: no cover
            raise ValueError("Minimum limit cannot be higher than maximum")

        self._max_value = value
        self.setValue(self.value())


# this is redefined from above because the above object is a dummy object
# we use dummy objects to allow the module to import when PyQt5 isn't installed
class RangeGroup(QHBoxLayout):
    """Range group box widget."""

    def __init__(self, parent, callback, minimum=0.0, maximum=20.0, value=1.0):
        """Initialize the range widget."""
        super(RangeGroup, self).__init__(parent)
        self.slider = DoubleSlider(QtCore.Qt.Horizontal)
        self.slider.setTickInterval(0.1)
        self.slider.setMinimum(minimum)
        self.slider.setMaximum(maximum)
        self.slider.setValue(value)

        self.minimum = minimum
        self.maximum = maximum

        self.spinbox = QDoubleSpinBox(
            value=value, minimum=minimum, maximum=maximum, decimals=4
        )

        self.addWidget(self.slider)
        self.addWidget(self.spinbox)

        # Connect slider to spinbox
        self.slider.valueChanged.connect(self.update_spinbox)
        self.spinbox.valueChanged.connect(self.update_value)
        self.spinbox.valueChanged.connect(callback)

    def update_spinbox(self, value):
        """Set the value of the internal spinbox."""
        self.spinbox.setValue(self.slider.value())

    def update_value(self, value):
        """Update the value of the internal slider."""
        # if self.spinbox.value() < self.minimum:
        #     self.spinbox.setValue(self.minimum)
        # elif self.spinbox.value() > self.maximum:
        #     self.spinbox.setValue(self.maximum)

        self.slider.blockSignals(True)
        self.slider.setValue(self.spinbox.value())
        self.slider.blockSignals(False)

    @property
    def value(self):
        """Return the value of the internal spinbox."""
        return self.spinbox.value()

    @value.setter
    def value(self, new_value):
        """Set the value of the internal slider."""
        self.slider.setValue(new_value)
