import pytest

from pyvistaqt import BackgroundPlotter, MainWindow, MultiPlotter, QtInteractor


def test_no_qt_binding(no_qt):
    with pytest.raises(RuntimeError, match="No Qt binding"):
        BackgroundPlotter()
    with pytest.raises(RuntimeError, match="No Qt binding"):
        MainWindow()
    with pytest.raises(RuntimeError, match="No Qt binding"):
        MultiPlotter()
    with pytest.raises(RuntimeError, match="No Qt binding"):
        QtInteractor()
