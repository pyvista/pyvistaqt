"""Tests for typehinting."""
from __future__ import annotations

import typing

from mypy import api

if typing.TYPE_CHECKING:  # pragma: no cover
    from qtpy import QtWidgets


def test_import(
    qapp: QtWidgets.QApplication,  # pylint: disable=unused-argument
) -> None:
    """Regression test for `Issue #163`_.

    Args:
        qapp (QtWidgets.QApplication): ``pytest-qt`` fixture for holding
            the ``QApplication`` instance.

            A ``QApplication`` must exist before a ``QWidget`` can be
            created. This fixture is used implicitly in this test.

    .. _`Issue #163`:
       https://github.com/pyvista/pyvistaqt/issues/163
    """

    src = """
from pyvistaqt import MainWindow

window = MainWindow()
window.setWindowTitle('window')
"""

    stdout, _, _ = api.run(['-c', src])

    assert (
        '"MainWindow" has no attribute "setWindowTitle"' not in stdout
    )
