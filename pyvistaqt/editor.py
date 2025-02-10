"""This module contains the Qt scene editor."""

import weakref
from typing import List

from pyvista import Renderer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
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
from vtkmodules.vtkRenderingCore import vtkActor

from .window import MainWindow


class Editor(QDialog):
    """Basic scene editor."""

    def __init__(self, parent: MainWindow, renderers: List[Renderer]) -> None:
        """Initialize the Editor."""
        super().__init__(parent=parent)
        self.renderers = renderers
        del renderers

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.stacked_widget = QStackedWidget()
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.tree_widget)
        self.layout.addWidget(self.stacked_widget)

        def _selection_callback() -> None:
            try:
                items = self.tree_widget.selectedItems()
            # Already deleted
            except RuntimeError:  # pragma: no cover
                return
            for item in items:
                widget_idx = item.data(0, Qt.ItemDataRole.UserRole)
                self.stacked_widget.setCurrentIndex(widget_idx)

        self.tree_widget.itemSelectionChanged.connect(_selection_callback)

        self.setLayout(self.layout)
        self.setWindowTitle("Editor")
        self.setModal(True)

        self.update()

    def update(self) -> None:
        """Update the internal widget list."""
        self.tree_widget.clear()
        for idx, renderer in enumerate(self.renderers):
            actors = renderer.actors
            widget_idx = self.stacked_widget.addWidget(_get_renderer_widget(renderer))
            top_item = QTreeWidgetItem(self.tree_widget, [f"Renderer {idx}"])
            top_item.setData(0, Qt.ItemDataRole.UserRole, widget_idx)
            self.tree_widget.addTopLevelItem(top_item)
            for name, actor in actors.items():
                if actor is not None:
                    widget_idx = self.stacked_widget.addWidget(_get_actor_widget(actor))
                    child_item = QTreeWidgetItem(top_item, [name])
                    child_item.setData(0, Qt.ItemDataRole.UserRole, widget_idx)
                    top_item.addChild(child_item)
        self.tree_widget.expandAll()

    def toggle(self) -> None:
        """Toggle the editor visibility."""
        self.update()
        if self.isVisible():
            self.hide()
        else:
            self.show()


def _get_renderer_widget(renderer: Renderer) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout()
    axes = QCheckBox("Axes")
    if hasattr(renderer, "axes_widget"):
        axes.setChecked(renderer.axes_widget.GetEnabled())
    else:
        axes.setChecked(False)

    renderer_ref = weakref.ref(renderer)
    del renderer

    # axes
    def _axes_callback(state: bool) -> None:
        renderer = renderer_ref()
        if renderer is None or renderer.parent.iren is None:  # pragma: no cover
            return
        if state:
            renderer.show_axes()
        else:
            renderer.hide_axes()

    axes.toggled.connect(_axes_callback)
    layout.addWidget(axes)

    widget.setLayout(layout)
    return widget


def _get_actor_widget(actor: vtkActor) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout()

    prop = actor.GetProperty()

    # visibility
    set_vis_ref = weakref.ref(actor.SetVisibility)

    def _set_vis(visibility: bool) -> None:  # pragma: no cover
        set_vis = set_vis_ref()
        if set_vis is not None:
            set_vis(visibility)

    visibility = QCheckBox("Visibility")
    visibility.setChecked(actor.GetVisibility())
    visibility.toggled.connect(_set_vis)
    layout.addWidget(visibility)

    if prop is not None:
        # opacity
        tmp_layout = QHBoxLayout()
        opacity = QDoubleSpinBox()
        opacity.setMaximum(1.0)
        opacity.setValue(prop.GetOpacity())
        set_opacity_ref = weakref.ref(prop.SetOpacity)

        def _set_opacity(opacity: float) -> None:  # pragma: no cover
            set_opacity = set_opacity_ref()
            if set_opacity is not None:
                set_opacity(opacity)

        opacity.valueChanged.connect(_set_opacity)
        tmp_layout.addWidget(QLabel("Opacity"))
        tmp_layout.addWidget(opacity)
        layout.addLayout(tmp_layout)

    widget.setLayout(layout)
    return widget
