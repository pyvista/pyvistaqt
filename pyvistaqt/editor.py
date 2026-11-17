"""This module contains the Qt scene editor."""  # noqa: D404

from collections.abc import Iterable
import weakref

from pyvista import Renderer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox
from qtpy.QtWidgets import QDialog
from qtpy.QtWidgets import QDoubleSpinBox
from qtpy.QtWidgets import QHBoxLayout
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QStackedWidget
from qtpy.QtWidgets import QTreeWidget
from qtpy.QtWidgets import QTreeWidgetItem
from qtpy.QtWidgets import QVBoxLayout
from qtpy.QtWidgets import QWidget

from pyvistaqt._vtk import vtkActor

from .window import MainWindow


class Editor(QDialog):
    """Basic scene editor."""

    def __init__(self, parent: MainWindow, renderers: Iterable[Renderer]) -> None:
        """Initialize the Editor."""
        super().__init__(parent=parent)
        self.renderers = renderers
        del renderers

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.stacked_widget = QStackedWidget()
        # NB: use a local, not ``self.layout``, which would shadow
        # ``QWidget.layout()``.
        layout = QHBoxLayout()
        layout.addWidget(self.tree_widget)
        layout.addWidget(self.stacked_widget)

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

        self.setLayout(layout)
        self.setWindowTitle("Editor")
        self.setModal(True)

        self.update()

    def update(self) -> None:  # ty: ignore[incompatible-method-override]
        """Update the internal widget list (intentionally shadows QWidget.update)."""
        self.tree_widget.clear()
        while (page := self.stacked_widget.widget(0)) is not None:
            self.stacked_widget.removeWidget(page)
            page.deleteLater()
        for idx, renderer in enumerate(self.renderers):
            actors = renderer.actors
            widget_idx = self.stacked_widget.addWidget(_get_renderer_widget(renderer))
            top_item = QTreeWidgetItem(self.tree_widget, [f"Renderer {idx}"])
            top_item.setData(0, Qt.ItemDataRole.UserRole, widget_idx)
            self.tree_widget.addTopLevelItem(top_item)
            for name, actor in actors.items():
                if actor is not None:
                    # pyvista types ``renderer.actors`` values as the broader
                    # ``vtkProp``; here they are ``vtkActor``.
                    widget_idx = self.stacked_widget.addWidget(
                        _get_actor_widget(actor, renderer),  # ty: ignore[invalid-argument-type]
                    )
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
    axes_widget = getattr(renderer, "axes_widget", None)
    if axes_widget is not None:
        axes.setChecked(bool(axes_widget.GetEnabled()))
    else:
        axes.setChecked(False)

    renderer_ref = weakref.ref(renderer)
    del renderer

    # axes
    def _axes_callback(state: bool) -> None:  # noqa: FBT001
        renderer = renderer_ref()
        if renderer is None or renderer.parent is None or renderer.parent.iren is None:  # pragma: no cover
            return
        if state:
            renderer.show_axes()
        else:
            renderer.hide_axes()

    axes.toggled.connect(_axes_callback)
    layout.addWidget(axes)

    widget.setLayout(layout)
    return widget


def _get_actor_widget(actor: vtkActor, renderer: Renderer | None = None) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout()

    prop = actor.GetProperty()

    # Hold weak references so that the Qt widgets do not keep VTK objects
    # alive (a weakref to a bound method would die immediately, so reference
    # the actor and call its methods once resolved).
    actor_ref = weakref.ref(actor)
    renderer_ref = None if renderer is None else weakref.ref(renderer)
    del renderer

    def _render() -> None:
        renderer = None if renderer_ref is None else renderer_ref()
        if renderer is not None and renderer.parent is not None:
            renderer.parent.render()

    # visibility
    def _set_vis(visibility: bool) -> None:  # noqa: FBT001
        actor = actor_ref()
        if actor is not None:
            actor.SetVisibility(visibility)
            _render()

    visibility = QCheckBox("Visibility")
    visibility.setChecked(bool(actor.GetVisibility()))
    visibility.toggled.connect(_set_vis)
    layout.addWidget(visibility)

    if prop is not None:
        # opacity
        tmp_layout = QHBoxLayout()
        opacity = QDoubleSpinBox()
        opacity.setMaximum(1.0)
        opacity.setValue(prop.GetOpacity())

        def _set_opacity(opacity: float) -> None:
            # Resolve the property through the actor: a weakref to the
            # property wrapper itself could die while the actor lives.
            actor = actor_ref()
            if actor is not None:
                actor.GetProperty().SetOpacity(opacity)
                _render()

        opacity.valueChanged.connect(_set_opacity)
        tmp_layout.addWidget(QLabel("Opacity"))
        tmp_layout.addWidget(opacity)
        layout.addLayout(tmp_layout)

    widget.setLayout(layout)
    return widget
