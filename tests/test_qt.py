import importlib
import sys

import pytest

import pyvistaqt


def _check_qt_installed():
    try:
        from qtpy import QtCore  # noqa
    except Exception:
        return False
    else:
        return True


def test_no_qt_binding(monkeypatch):
    need_reload = False
    if _check_qt_installed():
        need_reload = True
        monkeypatch.setenv('QT_API', 'bad_name')
        sys.modules.pop('qtpy')
        assert 'qtpy' not in sys.modules
        with pytest.raises(RuntimeError, match='No Qt binding'):
            importlib.reload(pyvistaqt)
    monkeypatch.undo()
    if need_reload:
        importlib.reload(pyvistaqt)
        assert 'qtpy' in sys.modules
