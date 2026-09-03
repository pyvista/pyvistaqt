"""Resolve VTK classes from the backend selected by PyVista."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    # These imports are never evaluated at runtime. They preserve concrete
    # types for static analysis while runtime imports use PyVista's backend.
    from vtkmodules.vtkCommonCore import vtkObjectBase
    from vtkmodules.vtkRenderingCore import vtkActor
    from vtkmodules.vtkRenderingCore import vtkRenderer
    from vtkmodules.vtkRenderingOpenGL2 import vtkGenericOpenGLRenderWindow
    from vtkmodules.vtkRenderingUI import vtkGenericRenderWindowInteractor

__all__ = [
    "BACKEND_IS_FLAT",
    "VTK_BACKEND",
    "vtkActor",
    "vtkGenericOpenGLRenderWindow",
    "vtkGenericRenderWindowInteractor",
    "vtkObjectBase",
    "vtkRenderer",
]

try:  # PyVista >= 0.48
    _pyvista_vtk = importlib.import_module("pyvista._vtk")
except ModuleNotFoundError as error:  # PyVista < 0.48
    if error.name != "pyvista._vtk":
        raise
    _pyvista_vtk = importlib.import_module("pyvista.plotting._vtk")

# PyVista versions before backend selection was introduced always use stock
# VTK, so the defaults preserve compatibility with the minimum supported
# PyVista version.
VTK_BACKEND: str = getattr(_pyvista_vtk, "_VTK_ROOT", "vtkmodules")
BACKEND_IS_FLAT: bool = getattr(_pyvista_vtk, "_VTK_ROOT_IS_FLAT", False)

# PyVista's lazy VTK module exposes most classes used by pyvistaqt. Keep the
# exceptions here so a non-flat backend can resolve them from their modules.
_FALLBACK_MODULES: dict[str, str] = {
    "vtkGenericOpenGLRenderWindow": "vtkRenderingOpenGL2",
    "vtkObjectBase": "vtkCommonCore",
}


def __getattr__(name: str) -> Any:  # noqa: ANN401
    """Return a VTK class from the same backend PyVista uses."""
    try:
        return getattr(_pyvista_vtk, name)
    except AttributeError:
        pass

    if BACKEND_IS_FLAT:
        try:
            return getattr(importlib.import_module(VTK_BACKEND), name)
        except (AttributeError, ImportError):
            pass

    vtk_module = _FALLBACK_MODULES.get(name)
    if vtk_module is not None:
        try:
            return getattr(importlib.import_module(f"{VTK_BACKEND}.{vtk_module}"), name)
        except (AttributeError, ImportError) as error:
            msg = f"{name!r} is unavailable from the selected VTK backend {VTK_BACKEND!r}."
            raise AttributeError(msg) from error

    msg = f"{name!r} is not exposed by PyVista's VTK backend. Add its module to pyvistaqt._vtk._FALLBACK_MODULES."
    raise AttributeError(msg)
