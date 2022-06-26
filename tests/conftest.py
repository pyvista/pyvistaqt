import importlib
import sys

import pytest
from pyvista.plotting import system_supports_plotting

import pyvistaqt

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
    need_reload = False
    if _check_qt_installed():
        need_reload = True
        monkeypatch.setenv("QT_API", "bad_name")
        sys.modules.pop("qtpy")
        importlib.reload(pyvistaqt)
        assert "qtpy" not in sys.modules
    yield
    monkeypatch.undo()
    if need_reload:
        importlib.reload(pyvistaqt)
        assert "qtpy" in sys.modules
