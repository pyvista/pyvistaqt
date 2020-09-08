"""
This module contains the Qt scene editor.
"""

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class Editor(QDialog):
    """Basic scene editor."""

    def __init__(self, parent, renderers):
        """Initialize the Editor."""
        super().__init__(parent=parent)
        self.renderers = renderers

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.stacked_widget = QStackedWidget()
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.tree_widget)
        self.layout.addWidget(self.stacked_widget)

        def _selection_callback():
            for item in self.tree_widget.selectedItems():
                self.stacked_widget.setCurrentIndex(item._idx)

        self.tree_widget.itemSelectionChanged.connect(_selection_callback)

        self.setLayout(self.layout)
        self.setWindowTitle("Editor")
        self.setModal(True)

        self.update()

    def update(self):
        """Update the internal widget list."""
        self.tree_widget.clear()
        widget_idx = 0
        for idx, renderer in enumerate(self.renderers):
            actors = renderer._actors  # pylint: disable=protected-access
            top_item = QTreeWidgetItem(self.tree_widget, ["Renderer {}".format(idx)])
            top_item._idx = widget_idx
            self.tree_widget.addTopLevelItem(top_item)
            self.stacked_widget.insertWidget(widget_idx, _get_renderer_widget(renderer))
            widget_idx += 1
            for name, actor in actors.items():
                if actor is not None:
                    child_item = QTreeWidgetItem(top_item, [name])
                    child_item._idx = widget_idx
                    top_item.addChild(child_item)
                    self.stacked_widget.insertWidget(
                        widget_idx, _get_actor_widget(actor)
                    )
                    widget_idx += 1
            top_item.setExpanded(True)

    def toggle(self):
        """Toggle the editor visibility."""
        self.update()
        if self.isVisible():
            self.hide()
        else:
            self.show()


def _get_renderer_widget(renderer):
    widget = QWidget()
    return widget


def _get_actor_widget(actor):
    widget = QWidget()
    layout = QVBoxLayout()

    prop = actor.GetProperty()

    # visibility
    visibility = QCheckBox("Visibility")
    visibility.setChecked(actor.GetVisibility())
    visibility.toggled.connect(actor.SetVisibility)
    layout.addWidget(visibility)

    if prop is not None:
        # opacity
        tmp_layout = QHBoxLayout()
        opacity = QDoubleSpinBox()
        opacity.setMaximum(1.0)
        opacity.setValue(prop.GetOpacity())
        opacity.valueChanged.connect(prop.SetOpacity)
        tmp_layout.addWidget(QLabel("Opacity"))
        tmp_layout.addWidget(opacity)
        layout.addLayout(tmp_layout)

    widget.setLayout(layout)
    return widget
