"""PyVista package for 3D plotting and mesh analysis."""
from ._version import __version__

try:
    from qtpy import QtCore  # noqa
except Exception as exc:  # pragma: no cover # pylint: disable=broad-except
    _exc_msg = exc

    raise RuntimeError(f'No Qt binding was found, got: {_exc_msg}') from exc

else:
    from .plotting import BackgroundPlotter as BackgroundPlotter
    from .plotting import MultiPlotter as MultiPlotter
    from .plotting import QtInteractor as QtInteractor
    from .window import MainWindow as MainWindow


__all__ = [
    '__version__',
    'BackgroundPlotter',
    'MainWindow',
    'MultiPlotter',
    'QtInteractor',
]
