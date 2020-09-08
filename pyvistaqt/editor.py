"""
This module contains the Qt scene editor.
"""

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QListWidget,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class Editor(QDialog):
    """Basic scene editor."""

    def __init__(self, parent, actors):
        """Initialize the Editor."""
        super().__init__(parent=parent)
        self.actors = actors

        self.list_widget = QListWidget()
        self.stacked_widget = QStackedWidget()
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.stacked_widget)

        self.list_widget.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        self.list_widget.setCurrentRow(0)

        self.setLayout(self.layout)
        self.setWindowTitle("Editor")
        self.setModal(True)

        self.update()

    def update(self):
        """Update the internal widget list."""
        self.list_widget.clear()
        for name, actor in self.actors.items():
            if actor is not None:
                self.list_widget.addItem(name)
                widget = _get_properties(actor)
                self.stacked_widget.addWidget(widget)

    def toggle(self):
        """Toggle the editor visibility."""
        self.update()
        if self.isVisible():
            self.hide()
        else:
            self.show()


def _get_properties(actor):
    widget = QWidget()
    layout = QVBoxLayout()

    # visibility
    visibility = QCheckBox("Visibility")
    visibility.setChecked(actor.GetVisibility())
    visibility.toggled.connect(actor.SetVisibility)
    layout.addWidget(visibility)

    widget.setLayout(layout)
    return widget
