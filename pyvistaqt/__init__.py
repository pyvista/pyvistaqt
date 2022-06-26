"""PyVista package for 3D plotting and mesh analysis."""
# pylint: disable=useless-import-alias  # PEP 484 (mypy) requires redundant aliases
from __future__ import annotations

from ._version import __version__

# mypy <= 0.961 does not support conditional imports
# See `Issue 1297`_ and `Issue 1393`_
#
# .. _`Issue 1297`:
#    https://github.com/python/mypy/issues/1297
# .. _`Issue 1393`:
#    https://github.com/python/mypy/issues/1393#issuecomment-1153228303
try:
    from qtpy import QtCore as _QtCore
except Exception as exc:
    QtCore = None  # pylint: disable=invalid-name
    raise RuntimeError(f'No Qt binding was found, got: {exc}') from exc
else:
    QtCore = _QtCore
    from .plotting import (
        BackgroundPlotter as BackgroundPlotter,
        MultiPlotter as MultiPlotter,
        QtInteractor as QtInteractor,
    )
    from .window import MainWindow as MainWindow


__all__ = [
    '__version__',
    'BackgroundPlotter',
    'MainWindow',
    'MultiPlotter',
    'QtInteractor',
]
