"""PyVista package for 3D plotting and mesh analysis."""
from ._version import __version__


try:
    from qtpy import QtCore  # noqa
except ModuleNotFoundError:
    class _QtBindingError:
        def __init__(self, *args, **kwargs):
            raise RuntimeError('No Qt binding is found')

    class BackgroundPlotter(_QtBindingError):
        pass

    class MainWindow(_QtBindingError):
        pass

    class MultiPlotter(_QtBindingError):
        pass

    class QtInteractor(_QtBindingError):
        pass
else:
    from .plotting import BackgroundPlotter, MainWindow, MultiPlotter, QtInteractor


__all__ = [
    "__version__",
    "BackgroundPlotter",
    "MainWindow",
    "MultiPlotter",
    "QtInteractor",
]
