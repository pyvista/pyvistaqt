import os
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
)

from .utils import RangeGroup


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
    ):
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


class ScaleAxesDialog(QDialog):
    """Dialog to control axes scaling."""

    accepted = pyqtSignal(float)
    signal_close = pyqtSignal()

    def __init__(self, parent, plotter, show=True):
        """Initialize the scaling dialog."""
        super(ScaleAxesDialog, self).__init__(parent)
        self.setGeometry(300, 300, 50, 50)
        self.setMinimumWidth(500)
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

    def update_scale(self, value):
        """Update the scale of all actors in the plotter."""
        self.plotter.set_scale(
            self.x_slider_group.value,
            self.y_slider_group.value,
            self.z_slider_group.value,
        )
