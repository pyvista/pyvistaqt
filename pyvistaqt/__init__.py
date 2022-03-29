"""PyVista package for 3D plotting and mesh analysis."""
from ._version import __version__

try:
    from qtpy import QtCore  # noqa
except ModuleNotFoundError:

    # pylint: disable=too-few-public-methods,missing-class-docstring
    class _QtBindingError:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("No Qt binding is found")

    # pylint: disable=too-few-public-methods,missing-class-docstring
    class BackgroundPlotter(_QtBindingError):
        pass

    # pylint: disable=too-few-public-methods,missing-class-docstring
    class MainWindow(_QtBindingError):
        pass

    # pylint: disable=too-few-public-methods,missing-class-docstring
    class MultiPlotter(_QtBindingError):
        pass

    # pylint: disable=too-few-public-methods,missing-class-docstring
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
