"""This module contains utilities routines."""
from typing import Any, List, Optional, Type

import numpy as np  # type: ignore
import pyvista
import scooby  # type: ignore
from qtpy.QtWidgets import QApplication, QMenuBar


def resample_image(arr: np.ndarray, max_size: int = 400) -> np.ndarray:
    """Resample a square image to an image of max_size."""
    dim = np.max(arr.shape[0:2])
    max_size = min(max_size, dim)
    x_size, y_size, _ = arr.shape
    s_x = int(np.ceil(x_size / max_size))
    s_y = int(np.ceil(y_size / max_size))
    img = np.zeros((max_size, max_size, arr.shape[2]), dtype=arr.dtype)
    arr = arr[0:-1:s_x, 0:-1:s_y, :]
    x_l = (max_size - arr.shape[0]) // 2
    y_l = (max_size - arr.shape[1]) // 2
    img[x_l : arr.shape[0] + x_l, y_l : arr.shape[1] + y_l, :] = arr
    return img


def pad_image(arr: np.ndarray, max_size: int = 400) -> np.ndarray:
    """Pad an image to a square then resamples to max_size."""
    dim = np.max(arr.shape)
    img = np.zeros((dim, dim, arr.shape[2]), dtype=arr.dtype)
    x_l = (dim - arr.shape[0]) // 2
    y_l = (dim - arr.shape[1]) // 2
    img[x_l : arr.shape[0] + x_l, y_l : arr.shape[1] + y_l, :] = arr
    return resample_image(img, max_size=max_size)


def _check_type(var: Any, var_name: str, var_types: List[Type[Any]]) -> None:
    types = tuple(var_types)
    if not isinstance(var, types):
        raise TypeError(
            f"Expected type for ``{var_name}`` is {str(types)}"
            f" but {type(var)} was given."
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
        ipython.run_line_magic("gui", "qt")

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
