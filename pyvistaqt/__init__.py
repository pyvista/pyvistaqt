"""PyVista package for 3D plotting and mesh analysis."""  # noqa: EXE002

try:
    from importlib.metadata import version

    __version__ = version("pyvistaqt")
except Exception:  # pragma: no cover  # noqa: BLE001
    __version__ = "0.0.0"

from .plotting import BackgroundPlotter
from .plotting import MainWindow
from .plotting import MultiPlotter
from .plotting import QtInteractor

__all__ = [
    "BackgroundPlotter",
    "MainWindow",
    "MultiPlotter",
    "QtInteractor",
    "__version__",
]
