from __future__ import annotations  # noqa: D100

import gc

import pytest
import pyvista
from pyvista.plotting import system_supports_plotting
from refleak.testing import Snapshot
from refleak.testing import gc_collect_once

NO_PLOTTING = not system_supports_plotting()


def pytest_configure(config) -> None:
    """Configure pytest options."""
    # Fixtures
    for fixture in ("check_gc",):
        config.addinivalue_line("usefixtures", fixture)
    # Markers
    config.addinivalue_line("markers", "slow: mark a test as slow")


_phase_report_key = pytest.StashKey()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):  # noqa: ANN201, ARG001
    """Stash per-phase reports so fixtures can skip GC checks on failure."""
    outcome = yield
    rep = outcome.get_result()
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep


def _test_passed(request) -> bool:
    report = request.node.stash.get(_phase_report_key, {})
    return "call" in report and report["call"].outcome == "passed"


_vtk_object_base = None


def _is_vtk(obj) -> bool:
    """
    Check if an object is a VTK object (wrappers and subclasses included).

    An ``isinstance`` check, not a class-name-prefix one: VTK >= 9.6
    instantiates pythonic override subclasses whose names lack the ``vtk``
    prefix (``PolyData``, ``VTKAOSArray_vtkFloatArray``, ...).
    """
    global _vtk_object_base  # noqa: PLW0603
    if _vtk_object_base is None:
        from vtkmodules.vtkCommonCore import vtkObjectBase  # noqa: PLC0415

        _vtk_object_base = vtkObjectBase
    return isinstance(obj, _vtk_object_base)


def _drain_qt_events() -> None:
    """Flush pending Qt work, including deferred (deleteLater) deletions."""
    try:
        from qtpy.QtCore import QEvent  # noqa: PLC0415
        from qtpy.QtWidgets import QApplication  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return
    app = QApplication.instance()
    if app is None:
        return
    for _ in range(2):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.fixture(autouse=True)
def check_gc(request):  # noqa: ANN201
    """Ensure that all VTK objects created during a test are GC'ed."""
    from pyvistaqt import QtInteractor  # noqa: PLC0415

    # Snapshots so that process-lifetime leftovers (e.g. session-scoped
    # fixtures, the trame server singleton) are not blamed on this test.
    gc.collect()
    objs = gc.get_objects()  # scan the heap once, share across snapshots
    snap_qt = Snapshot(QtInteractor, objs=objs)
    snap_vtk = Snapshot(_is_vtk, label="VTK", objs=objs)
    del objs
    yield
    pyvista.close_all()
    _drain_qt_events()
    if not _test_passed(request):
        return
    when = f"teardown of {request.node.name}"
    gc_collect_once(request)
    objs = gc.get_objects()
    # No plotter/interactor created during a test may survive it
    # (BackgroundPlotter is a QtInteractor subclass, so this covers both) ...
    snap_qt.assert_no_new(when, request=request, objs=objs)
    # ... and neither may any VTK object created during the test.
    snap_vtk.assert_no_new(when, request=request, objs=objs)
    del objs


@pytest.fixture
def plotting() -> None:
    """Require plotting."""
    if NO_PLOTTING:
        pytest.skip(NO_PLOTTING, reason="Requires system to support plotting")
