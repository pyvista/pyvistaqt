"""PyVista package for 3D plotting and mesh analysis."""

try:
    from importlib.metadata import version

    __version__ = version("pyvistaqt")
except Exception:  # pragma: no cover # pylint: disable=broad-exception-caught
    try:
        from ._version import __version__
    except ImportError:
        __version__ = '0.0.0'

try:
    from qtpy import QtCore  # noqa
except Exception as exc:  # pragma: no cover # pylint: disable=broad-except
    _exc_msg = exc

    # pylint: disable=too-few-public-methods
    class _QtBindingError:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(f"No Qt binding was found, got: {_exc_msg}")

    # pylint: disable=too-few-public-methods
    class BackgroundPlotter(_QtBindingError):
        """Handle Qt binding error for BackgroundPlotter."""

    # pylint: disable=too-few-public-methods
    class MainWindow(_QtBindingError):
        """Handle Qt binding error for MainWindow."""

    # pylint: disable=too-few-public-methods
    class MultiPlotter(_QtBindingError):
        """Handle Qt binding error for MultiPlotter."""

    # pylint: disable=too-few-public-methods
    class QtInteractor(_QtBindingError):
        """Handle Qt binding error for QtInteractor."""

else:
    from .plotting import BackgroundPlotter, MainWindow, MultiPlotter, QtInteractor


__all__ = [
    "__version__",
    "BackgroundPlotter",
    "MainWindow",
    "MultiPlotter",
    "QtInteractor",
]
