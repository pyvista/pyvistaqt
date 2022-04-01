import pytest
import importlib
import qtpy
from pyvista.plotting import system_supports_plotting

NO_PLOTTING = not system_supports_plotting()


def _check_qt_installed():
    try:
        from qtpy import QtCore  # noqa
    except Exception:
        return False
    else:
        return True


@pytest.fixture()
def plotting():
    """Require plotting."""
    if NO_PLOTTING:
        pytest.skip(NO_PLOTTING, reason="Requires system to support plotting")
    yield


@pytest.fixture()
def no_qt(monkeypatch):
    """Require plotting."""
    if _check_qt_installed():
        monkeypatch.setenv('QT_API', 'bad_name')
        importlib.reload(qtpy)
    yield
