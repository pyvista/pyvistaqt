"""PyVista package for 3D plotting and mesh analysis."""  # noqa: EXE002

from __future__ import annotations

try:
    from importlib.metadata import version

    __version__ = version("pyvistaqt")
except Exception:  # pragma: no cover # pylint: disable=broad-exception-caught  # noqa: BLE001
    try:
        from ._version import __version__
    except ImportError:
        __version__ = "0.0.0"

try:
    from qtpy import QtCore  # noqa: F401
except Exception as exc:  # pragma: no cover # pylint: disable=broad-except  # noqa: BLE001
    _exc_msg = exc

    # pylint: disable=too-few-public-methods
    class _QtBindingError:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, ARG002
            msg = f"No Qt binding was found, got: {_exc_msg}"
            raise RuntimeError(msg)

    # pylint: disable=too-few-public-methods
    class BackgroundPlotter(_QtBindingError):  # noqa: N818
        """Handle Qt binding error for BackgroundPlotter."""

    # pylint: disable=too-few-public-methods
    class MainWindow(_QtBindingError):  # noqa: N818
        """Handle Qt binding error for MainWindow."""

    # pylint: disable=too-few-public-methods
    class MultiPlotter(_QtBindingError):  # noqa: N818
        """Handle Qt binding error for MultiPlotter."""

    # pylint: disable=too-few-public-methods
    class QtInteractor(_QtBindingError):  # noqa: N818
        """Handle Qt binding error for QtInteractor."""

else:
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
