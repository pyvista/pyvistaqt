"""This module contains utilities routines."""
from typing import Any, List, Optional, Type

import pyvista
import scooby  # type: ignore
from qtpy.QtWidgets import QApplication, QMenuBar


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
