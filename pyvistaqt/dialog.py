"""
TODO: Add docstring
"""
import os

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QSlider,
)


class FileDialog(QFileDialog):
    """Generic file query.

    It emits a signal when a file is selected and
    the dialog was property closed.
    """

    dlg_accepted = pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        filefilter=None,
        save_mode=True,
        show=True,
        callback=None,
        directory=False,
    ):  # pylint: disable=too-many-arguments
        """Initialize the file dialog."""
        super(FileDialog, self).__init__(parent)

        if filefilter is not None:
            self.setNameFilters(filefilter)

        self.setOption(QFileDialog.DontUseNativeDialog)
        self.accepted.connect(self.emit_accepted)

        if directory:
            self.FileMode(QFileDialog.DirectoryOnly)
            self.setOption(QFileDialog.ShowDirsOnly, True)

        if save_mode:
            self.setAcceptMode(QFileDialog.AcceptSave)

        if callback is not None:
            self.dlg_accepted.connect(callback)

        if show:  # pragma: no cover
            self.show()

    def emit_accepted(self):
        """Send signal that the file dialog was closed properly.

        Sends:
        filename

        """
        if self.result():
            filename = self.selectedFiles()[0]
            if os.path.isdir(os.path.dirname(filename)):
                self.dlg_accepted.emit(filename)


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

        super().set_minimum(0)
        super().set_maximum(self._max_int)

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

    def setValue(self, value):  # pylint: disable=invalid-name
        """Set the value of the slider."""
        super().set_value(
            int((value - self._min_value) / self._value_range * self._max_int)
        )

    def set_minimum(self, value):
        """Set the minimum value of the slider."""
        if value > self._max_value:  # pragma: no cover
            raise ValueError("Minimum limit cannot be higher than maximum")

        self._min_value = value
        self.set_value(self.value())

    def set_maximum(self, value):
        """Set the maximum value of the slider."""
        if value < self._min_value:  # pragma: no cover
            raise ValueError("Minimum limit cannot be higher than maximum")

        self._max_value = value
        self.set_value(self.value())


# this is redefined from above because the above object is a dummy object
# we use dummy objects to allow the module to import when PyQt5 isn't installed
class RangeGroup(QHBoxLayout):
    """Range group box widget."""

    def __init__(
        self, parent, callback, minimum=0.0, maximum=20.0, value=1.0
    ):  # pylint: disable=too-many-arguments
        """Initialize the range widget."""
        super(RangeGroup, self).__init__(parent)
        self.slider = DoubleSlider(QtCore.Qt.Horizontal)
        self.slider.setTickInterval(0.1)
        self.slider.set_minimum(minimum)
        self.slider.set_maximum(maximum)
        self.slider.set_value(value)

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

    def update_spinbox(self):
        """Set the value of the internal spinbox."""
        self.spinbox.set_value(self.slider.value())

    def update_value(self):
        """Update the value of the internal slider."""
        # if self.spinbox.value() < self.minimum:
        #     self.spinbox.set_value(self.minimum)
        # elif self.spinbox.value() > self.maximum:
        #     self.spinbox.set_value(self.maximum)

        self.slider.blockSignals(True)
        self.slider.set_value(self.spinbox.value())
        self.slider.blockSignals(False)

    @property
    def value(self):
        """Return the value of the internal spinbox."""
        return self.spinbox.value()

    @value.setter
    def value(self, new_value):
        """Set the value of the internal slider."""
        self.slider.set_value(new_value)


class ScaleAxesDialog(QDialog):
    """Dialog to control axes scaling."""

    accepted = pyqtSignal(float)
    signal_close = pyqtSignal()

    def __init__(self, parent, plotter, show=True):
        """Initialize the scaling dialog."""
        super(ScaleAxesDialog, self).__init__(parent)
        self.setGeometry(300, 300, 50, 50)
        self.set_minimumWidth(500)
        self.signal_close.connect(self.close)
        self.plotter = plotter
        self.plotter.app_window.signal_close.connect(self.close)

        self.x_slider_group = RangeGroup(
            parent, self.update_scale, value=plotter.scale[0]
        )
        self.y_slider_group = RangeGroup(
            parent, self.update_scale, value=plotter.scale[1]
        )
        self.z_slider_group = RangeGroup(
            parent, self.update_scale, value=plotter.scale[2]
        )

        form_layout = QFormLayout(self)
        form_layout.addRow("X Scale", self.x_slider_group)
        form_layout.addRow("Y Scale", self.y_slider_group)
        form_layout.addRow("Z Scale", self.z_slider_group)

        self.setLayout(form_layout)

        if show:  # pragma: no cover
            self.show()

    def update_scale(self):
        """Update the scale of all actors in the plotter."""
        self.plotter.set_scale(
            self.x_slider_group.value,
            self.y_slider_group.value,
            self.z_slider_group.value,
        )
