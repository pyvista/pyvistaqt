from __future__ import annotations  # noqa: D100

import gc
import importlib
import inspect
import sys

import pytest
import pyvista
from pyvista.plotting import system_supports_plotting

import pyvistaqt

NO_PLOTTING = not system_supports_plotting()


def pytest_configure(config) -> None:
    """Configure pytest options."""
    # Fixtures
    for fixture in ("check_gc",):
        config.addinivalue_line("usefixtures", fixture)
    # Markers
    for marker in ("allow_bad_gc", "allow_bad_gc_pyside"):
        config.addinivalue_line("markers", marker)


# Adapted from PyVista
def _is_vtk(obj):  # noqa: ANN202
    try:
        return obj.__class__.__name__.startswith("vtk")
    except Exception:  # old Python sometimes no __class__.__name__  # noqa: BLE001
        return False


def _check_qt_installed() -> bool:
    try:
        from qtpy import QtCore  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    else:
        return True


@pytest.fixture(autouse=True)
def check_gc(request):  # noqa: ANN201, C901
    """Ensure that all VTK objects are garbage-collected by Python."""
    if "test_ipython" in request.node.name:  # XXX this keeps a ref  # noqa: FIX003, TD001, TD002, TD003, TD004
        yield
        return
    try:
        from qtpy import API_NAME
    except Exception:  # noqa: BLE001
        API_NAME = ""  # noqa: N806
    marks = {mark.name for mark in request.node.iter_markers()}
    if "allow_bad_gc" in marks:
        yield
        return
    if "allow_bad_gc_pyside" in marks and API_NAME.lower().startswith("pyside"):
        yield
        return
    gc.collect()
    before = {id(o) for o in gc.get_objects() if _is_vtk(o)}
    yield
    pyvista.close_all()
    gc.collect()
    after = [o for o in gc.get_objects() if _is_vtk(o) and id(o) not in before]
    msg = "Not all objects GCed:\n"
    for obj in after:
        cn = obj.__class__.__name__
        cf = inspect.currentframe()
        referrers = [v for v in gc.get_referrers(obj) if v is not after and v is not cf]
        del cf
        for ri, referrer in enumerate(referrers):
            if isinstance(referrer, dict):
                for k, v in referrer.items():
                    if k is obj:
                        referrers[ri] = "dict: d key"
                        del k, v
                        break
                    elif v is obj:
                        referrers[ri] = f"dict: d[{k!r}]"
                        # raise RuntimeError(referrers[ri])  # noqa: ERA001
                        del k, v
                        break
                    del k, v
                else:
                    referrers[ri] = f"dict: len={len(referrer)}"
            else:
                referrers[ri] = repr(referrer)
            del ri, referrer
        msg += f"{cn}: {referrers}\n"
        del cn, referrers
    assert len(after) == 0, msg


@pytest.fixture
def plotting() -> None:
    """Require plotting."""
    if NO_PLOTTING:
        pytest.skip(NO_PLOTTING, reason="Requires system to support plotting")


@pytest.fixture
def no_qt(monkeypatch):  # noqa: ANN201
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
