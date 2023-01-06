import pytest


def test_no_qt_binding(no_qt):
    from pyvistaqt import BackgroundPlotter, MainWindow, MultiPlotter, QtInteractor
    with pytest.raises(RuntimeError, match="No Qt binding"):
        BackgroundPlotter()
    with pytest.raises(RuntimeError, match="No Qt binding"):
        MainWindow()
    with pytest.raises(RuntimeError, match="No Qt binding"):
        MultiPlotter()
    with pytest.raises(RuntimeError, match="No Qt binding"):
        QtInteractor()
