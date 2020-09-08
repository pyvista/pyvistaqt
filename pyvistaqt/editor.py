"""
This module contains the Qt scene editor.
"""

from PyQt5.QtWidgets import (QListWidget, QStackedWidget,
                             QDialog, QHBoxLayout, QWidget,
                             QVBoxLayout, QCheckBox)


class Editor(QDialog):

    def __init__(self, parent, actors):
        super().__init__(parent=parent)
        self.actors = actors

        self.list_widget = QListWidget()
        self.stacked_widget = QStackedWidget()
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.stacked_widget)

        self.list_widget.currentRowChanged.connect(
            self.stacked_widget.setCurrentIndex)
        self.list_widget.setCurrentRow(0)

        self.setLayout(self.layout)
        self.setWindowTitle("Editor")
        self.setModal(True)

        self.update()

    def update(self):
        self.list_widget.clear()
        for name, actor in self.actors.items():
            if actor is not None:
                self.list_widget.addItem(name)
                widget = _get_properties(actor)
                self.stacked_widget.addWidget(widget)

    def toggle(self):
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
    visibility.toggled.connect(
        lambda x: actor.SetVisibility(x)
    )
    layout.addWidget(visibility)

    widget.setLayout(layout)
    return widget
