from __future__ import annotations  # noqa: D100

import pytest


def test_no_qt_binding(no_qt) -> None:  # noqa: ARG001, D103
    from pyvistaqt import BackgroundPlotter
    from pyvistaqt import MainWindow
    from pyvistaqt import MultiPlotter
    from pyvistaqt import QtInteractor

    with pytest.raises(RuntimeError, match="No Qt binding"):
        BackgroundPlotter()
    with pytest.raises(RuntimeError, match="No Qt binding"):
        MainWindow()
    with pytest.raises(RuntimeError, match="No Qt binding"):
        MultiPlotter()
    with pytest.raises(RuntimeError, match="No Qt binding"):
        QtInteractor()
