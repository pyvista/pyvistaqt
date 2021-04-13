"""This module contains utilities routines."""
from typing import Any, List, Optional, Type

import pyvista
import scooby  # type: ignore
from pyvista.plotting.plotting import BasePlotter
from qtpy.QtWidgets import (
    QApplication,
    QMenuBar,
)


def _check_type(var: Any, var_name: str, var_types: List[Type[Any]]) -> None:
    types = tuple(var_types)
    if not isinstance(var, types):
        raise TypeError(
            "Expected type for ``{}`` is {}"
            " but {} was given.".format(var_name, str(types), type(var))
        )


def _create_menu_bar(parent: Any) -> QMenuBar:
    """Create a menu bar.

    The menu bar is expected to behave consistently
    for every operating system since `setNativeMenuBar(False)`
    is called by default and therefore lifetime and ownership can
    be tested.
    """
    menu_bar = QMenuBar(parent=parent)
    menu_bar.setNativeMenuBar(False)
    if parent is not None:
        parent.setMenuBar(menu_bar)
    return menu_bar


def _setup_ipython(ipython: Any = None) -> Any:
    # ipython magic
    if scooby.in_ipython():  # pragma: no cover
        # pylint: disable=import-outside-toplevel
        from IPython import get_ipython

        ipython = get_ipython()
        ipython.magic("gui qt")

        # pylint: disable=redefined-outer-name
        # pylint: disable=import-outside-toplevel
        from IPython.external.qt_for_kernel import QtGui

        QtGui.QApplication.instance()
    return ipython


def _setup_application(app: Optional[QApplication] = None) -> QApplication:
    # run within python
    if app is None:
        app = QApplication.instance()
        if not app:  # pragma: no cover
            app = QApplication(["PyVista"])
    return app


def _setup_off_screen(off_screen: Optional[bool] = None) -> bool:
    if off_screen is None:
        off_screen = pyvista.OFF_SCREEN
    return off_screen


def _setup_interactor(plotter: BasePlotter, off_screen: bool) -> Any:
    if off_screen:
        return None
    try:
        from pyvista.plotting.render_window_interactor import RenderWindowInteractor

        iren = RenderWindowInteractor(
            plotter, interactor=plotter.ren_win.GetInteractor()
        )
        iren.interactor.RemoveObservers("MouseMoveEvent")  # slows window update?
        iren.initialize()
    except ImportError:
        iren = plotter.ren_win.GetInteractor()
        iren.RemoveObservers("MouseMoveEvent")  # slows window update?
        iren.Initialize()
    return iren


def _setup_key_press(plotter: BasePlotter):
    try:
        setattr(plotter, "_observers", {})
        plotter.iren.add_observer("KeyPressEvent", plotter.key_press_event)
    except AttributeError:
        plotter._add_observer("KeyPressEvent", plotter.key_press_event)
