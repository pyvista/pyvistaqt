"""PyVista package for 3D plotting and mesh analysis."""
from ._version import __version__


try:
    from qtpy import QtCore  # noqa
except ModuleNotFoundError:
    class BackgroundPlotter:
        def __init__(self, *args, **kwargs):
            raise RuntimeError('No Qt binding found')

    class MainWindow:
        def __init__(self, *args, **kwargs):
            raise RuntimeError('No Qt binding found')

    class MultiPlotter:
        def __init__(self, *args, **kwargs):
            raise RuntimeError('No Qt binding found')

    class QtInteractor:
        def __init__(self, *args, **kwargs):
            raise RuntimeError('No Qt binding found')
else:
    from .plotting import BackgroundPlotter, MainWindow, MultiPlotter, QtInteractor


__all__ = [
    "__version__",
    "BackgroundPlotter",
    "MainWindow",
    "MultiPlotter",
    "QtInteractor",
]
