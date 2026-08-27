from __future__ import annotations  # noqa: D100

import contextlib
import gc
import logging
import os
import os.path as op
import platform
import re
import sys
import threading
import time
import weakref

import numpy as np
import pytest
from pytestqt.exceptions import TimeoutError as QtBotTimeoutError
import pyvista
from pyvista.plotting import Renderer
from pyvista.plotting.utilities.gl_checks import check_depth_peeling
from qtpy import API_NAME
from qtpy import QtCore
from qtpy.QtCore import QMimeData
from qtpy.QtCore import QPoint
from qtpy.QtCore import QPointF
from qtpy.QtCore import Qt
from qtpy.QtCore import QUrl
from qtpy.QtGui import QDragEnterEvent
from qtpy.QtGui import QDropEvent
from qtpy.QtWidgets import QAction
from qtpy.QtWidgets import QCheckBox
from qtpy.QtWidgets import QFrame
from qtpy.QtWidgets import QGestureEvent
from qtpy.QtWidgets import QMenuBar
from qtpy.QtWidgets import QPinchGesture
from qtpy.QtWidgets import QStackedWidget
from qtpy.QtWidgets import QToolBar
from qtpy.QtWidgets import QTreeWidget
from qtpy.QtWidgets import QVBoxLayout
import vtk

from pyvistaqt.plotting import LOG
from pyvistaqt.plotting import global_theme

try:
    from pyvista.plotting.utilities import Scraper
except ImportError:  # PV < 0.40
    from pyvista.utilities import Scraper

import pyvistaqt
from pyvistaqt import BackgroundPlotter
from pyvistaqt import MainWindow
from pyvistaqt import MultiPlotter
from pyvistaqt import QtInteractor
from pyvistaqt.dialog import FileDialog
from pyvistaqt.editor import Editor
from pyvistaqt.plotting import Counter
from pyvistaqt.plotting import QTimer
from pyvistaqt.plotting import QVTKRenderWindowInteractor
from pyvistaqt.utils import _TERMINAL_OUTPUT_GUARDS
from pyvistaqt.utils import _check_type
from pyvistaqt.utils import _create_menu_bar
from pyvistaqt.utils import _declared_gl_backend
from pyvistaqt.utils import _gl_backend_for
from pyvistaqt.utils import _setup_application
from pyvistaqt.utils import _setup_terminal_output_fix
from pyvistaqt.utils import _TerminalOpostGuard


class TstWindow(MainWindow):  # noqa: D101
    def __init__(self, parent=None, show=True, off_screen=True) -> None:  # noqa: FBT002, D107
        MainWindow.__init__(self, parent)

        self.frame = QFrame()
        vlayout = QVBoxLayout()
        self.vtk_widget = QtInteractor(
            parent=self.frame,
            off_screen=off_screen,
            stereo=False,
        )
        vlayout.addWidget(self.vtk_widget.interactor)

        self.frame.setLayout(vlayout)
        self.setCentralWidget(self.frame)

        mainMenu = _create_menu_bar(parent=self)  # noqa: N806

        fileMenu = mainMenu.addMenu("File")  # noqa: N806
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        fileMenu.addAction(self.exit_action)

        meshMenu = mainMenu.addMenu("Mesh")  # noqa: N806
        self.add_sphere_action = QAction("Add Sphere", self)
        self.exit_action.setShortcut("Ctrl+A")
        self.add_sphere_action.triggered.connect(self.add_sphere)
        meshMenu.addAction(self.add_sphere_action)

        self.signal_close.connect(self.vtk_widget.close)

        if show:
            self.show()

    def add_sphere(self) -> None:  # noqa: D102
        sphere = pyvista.Sphere(phi_resolution=6, theta_resolution=6)
        self.vtk_widget.add_mesh(sphere)
        self.vtk_widget.reset_camera()


def test_create_menu_bar(qtbot) -> None:  # noqa: D103
    menu_bar = _create_menu_bar(parent=None)
    qtbot.addWidget(menu_bar)


def test_setup_application(qapp) -> None:  # noqa: D103
    _setup_application(qapp)


def test_setup_terminal_output_fix_noop_when_not_interactive(qapp) -> None:
    """The terminal fix must not install itself outside an interactive REPL."""
    # pytest is not run with ``python -i``, so neither ``sys.ps1`` nor the
    # interactive flag is set and the guard must be a no-op.
    assert not hasattr(sys, "ps1")
    assert not sys.flags.interactive
    before = len(_TERMINAL_OUTPUT_GUARDS)
    _setup_terminal_output_fix(qapp)
    assert len(_TERMINAL_OUTPUT_GUARDS) == before


def test_terminal_opost_guard(monkeypatch) -> None:
    """The guard restores OPOST while events run, then hands the tty back raw."""
    termios = pytest.importorskip("termios")

    # A terminal in raw mode: output post-processing (index 1 == oflag) cleared.
    state = [[0, 0, 0, 0, 0, 0, []]]

    def fake_tcgetattr(_fd: int) -> list:
        return list(state[0])

    def fake_tcsetattr(_fd: int, _when: int, attrs: list) -> None:
        state[0] = list(attrs)

    monkeypatch.setattr(termios, "tcgetattr", fake_tcgetattr)
    monkeypatch.setattr(termios, "tcsetattr", fake_tcsetattr)

    guard = _TerminalOpostGuard(fd=1)
    guard.enable()
    assert state[0][1] & termios.OPOST  # post-processing turned back on
    assert state[0][1] & termios.ONLCR
    guard.restore()
    assert not state[0][1] & termios.OPOST  # handed back exactly as it was

    # ``enable`` is a no-op when the terminal is already sane.
    state[0][1] = termios.OPOST | termios.ONLCR
    guard.enable()
    guard.restore()  # nothing saved -> no change
    assert state[0][1] == termios.OPOST | termios.ONLCR


def test_file_dialog(tmpdir, qtbot) -> None:  # noqa: D103
    dialog = FileDialog(
        filefilter=None,
        directory=False,
        save_mode=False,
        show=False,
    )
    qtbot.addWidget(dialog)

    dialog.emit_accepted()  # test no result

    p = tmpdir.mkdir("tmp").join("foo.png")
    p.write("foo")
    assert os.path.isfile(p)  # noqa: PTH113

    filename = str(p)
    dialog.selectFile(filename)

    # show the dialog
    assert not dialog.isVisible()
    with wait_exposed(qtbot, dialog):
        dialog.show()
    assert dialog.isVisible()

    # synchronise signal and callback
    with qtbot.wait_signals([dialog.dlg_accepted], timeout=1000):
        dialog.accept()
    assert not dialog.isVisible()  # dialog is closed after accept()


def test_check_type() -> None:  # noqa: D103
    with pytest.raises(TypeError, match="Expected type"):
        _check_type(0, "foo", [str])
    _check_type(0, "foo", [int, float])
    _check_type("foo", "foo", [str])


@pytest.fixture
def debug_log_level():  # noqa: ANN201
    """Set the log level to debug for a test."""
    old_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        LOG.setLevel(old_level)


# Preserve shim in case things break again, see
# https://github.com/pyvista/pyvistaqt/pull/810
BAD_INTERACTION = False

_NO_GL: bool | None = None


def _no_gl() -> bool:
    """
    Return True where Qt cannot provide a GL context at all.

    On macOS >= 26 with Qt >= 6.10 the Apple software renderer is refused
    outright (QOpenGLWidget is unsupported; see rwi.py invariant #7), so there
    is no context for tests that need one to inspect. Detect it the same way
    ``test_report_capabilities_unrealized`` does and cache it.
    """
    global _NO_GL  # noqa: PLW0603
    if _NO_GL is None:
        from qtpy.QtGui import QOpenGLContext  # noqa: PLC0415

        _NO_GL = not QOpenGLContext().create()
    return _NO_GL


@contextlib.contextmanager
def wait_exposed(qtbot, widget, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ANN201,ANN003
    """
    Wrap qtbot.wait_exposed, tolerating slow compositing.

    pytest-qt defaults to 5 s, which is not enough on a loaded CI VM driving
    software GL: ``test_background_plotter_export_files[True]`` intermittently
    timed out waiting for its FileDialog on macOS arm64 while the very same
    wait passed in the ``[False]`` parametrization and in two other dialog
    tests of the same run. Exposure does happen there, just late, so wait
    longer rather than skip -- this costs nothing when the window maps
    promptly.
    """
    if BAD_INTERACTION or _no_gl():
        yield
        return
    kwargs.setdefault("timeout", 30_000)
    try:
        with qtbot.wait_exposed(widget, **kwargs):
            yield
    except QtBotTimeoutError:
        # The window servers on the macOS CI VMs sometimes never expose a window at all;
        # tests that need pixels render synchronously and read the buffer, so keep going.
        if sys.platform != "darwin":
            raise
        print(f"Never exposed: {widget}")


def test_mouse_interactions(qtbot, debug_log_level) -> None:  # noqa: D103,ARG001
    plotter = BackgroundPlotter()
    window = plotter.app_window
    interactor = plotter.interactor
    qtbot.addWidget(window)
    point = QPoint(0, 0)
    if not BAD_INTERACTION:
        qtbot.mouseMove(interactor, point)
        qtbot.mouseClick(interactor, QtCore.Qt.LeftButton)
    plotter.close()


def test_ipython(qapp) -> None:  # noqa: ARG001, D103
    IPython = pytest.importorskip("IPython")  # noqa: N806
    cmd = "from pyvistaqt import BackgroundPlotter as Plotter;p = Plotter(show=False, off_screen=False); p.close(); del p; exit()"
    IPython.start_ipython(argv=["-c", cmd])


class SuperWindow(MainWindow):  # noqa: D101
    pass


def test_report_capabilities_unrealized(qtbot) -> None:
    """GPU queries must work on a never-shown plotter (as MNE's _is_osmesa does)."""
    from qtpy.QtGui import QOpenGLContext  # noqa: PLC0415

    if not QOpenGLContext().create():
        pytest.skip("Qt did not provide a GL context (macOS software GL)")
    plotter = BackgroundPlotter(show=False, off_screen=False)
    qtbot.addWidget(plotter.app_window)
    caps = plotter.ren_win.ReportCapabilities()
    assert "OpenGL" in caps
    plotter.close()


def test_screenshot_unrealized(qtbot) -> None:
    """
    ``image`` must render at the requested size on a never-shown plotter.

    The old native-window interactor created its GL context (at the requested
    size) on demand, so rendering APIs worked before the window was ever
    shown; MNE relies on this. The FBO widget has no context until it paints
    and only learns its size in ``resizeGL``, so this needs the widget to be
    realized offscreen *and* the size seeded into VTK first -- two separate
    regressions that MNE, not pyvistaqt, caught.
    """
    if _no_gl():
        pytest.skip("Qt did not provide a GL context (macOS software GL)")
    size = (300, 300)
    plotter = BackgroundPlotter(show=False, off_screen=False, window_size=size)
    qtbot.addWidget(plotter.app_window)
    plotter.set_background("black")
    plotter.add_mesh(pyvista.Sphere(), color="white")
    assert plotter.interactor._ctx is None, "widget was realized before we asked"  # noqa: SLF001

    img = np.array(plotter.image)  # must not raise, nor come back empty/0x0

    dpr = plotter.interactor.devicePixelRatioF()
    assert img.shape == (round(size[1] * dpr), round(size[0] * dpr), 3)
    assert 0.0 < img.any(-1).mean() < 1.0  # the sphere actually rendered
    plotter.close()


def test_close_removes_vtk_observers(qtbot) -> None:
    """
    ``close`` must drop VTK's C++-side references to our bound methods.

    VTK holds a strong reference to each observer, which pins the widget
    invisibly to Python's GC for as long as the render window lives.
    """
    plotter = BackgroundPlotter(show=False, off_screen=False)
    qtbot.addWidget(plotter.app_window)
    ren_win = plotter.ren_win  # close() drops the plotter's own reference
    assert ren_win.HasObserver("WindowMakeCurrentEvent")
    plotter.close()
    for event in ("WindowMakeCurrentEvent", "WindowIsCurrentEvent", "WindowFrameEvent"):
        assert not ren_win.HasObserver(event), event


def test_default_surface_format(qtbot) -> None:
    """
    The GL format must be installed process-wide (rwi.py invariant 2).

    A per-widget ``setFormat`` makes the widget's context incompatible with
    its top-level window's share context on Wayland and the widget silently
    composites black, so the format has to land on ``setDefaultFormat``.
    """
    from qtpy.QtGui import QSurfaceFormat  # noqa: PLC0415

    plotter = BackgroundPlotter(show=False, off_screen=False)
    qtbot.addWidget(plotter.app_window)
    fmt = QSurfaceFormat.defaultFormat()
    assert (fmt.majorVersion(), fmt.minorVersion()) >= (3, 2)
    assert fmt.profile() == QSurfaceFormat.OpenGLContextProfile.CoreProfile
    assert fmt.renderableType() == QSurfaceFormat.RenderableType.OpenGL
    plotter.close()


def test_close_after_parent_destroyed(qtbot, qapp, capsys) -> None:
    """
    A child interactor must survive its context dying with its parent.

    Deleting the parent window destroys the C++ widget (and its GL context)
    before the parent's ``destroyed`` -> ``close`` connection runs Finalize
    through the make-current observer, so ``aboutToBeDestroyed`` never
    reaches ``_cleanup_context`` and the observer holds a stale wrapper.
    VTK swallows the resulting RuntimeError, printing a traceback, and then
    releases its GL objects against whatever context is current instead.
    """
    if _no_gl():
        pytest.skip("Qt did not provide a GL context (macOS software GL)")
    window = MainWindow()
    frame = QFrame(parent=window)
    layout = QVBoxLayout()
    interactor = QtInteractor(parent=frame)
    layout.addWidget(interactor.interactor)
    frame.setLayout(layout)
    window.setCentralWidget(frame)
    interactor.add_mesh(pyvista.Sphere())
    with wait_exposed(qtbot, window):
        window.show()
    assert interactor._ctx is not None, "widget never got a GL context"  # noqa: SLF001
    weak_interactor = weakref.ref(interactor)
    capsys.readouterr()  # drop anything printed during setup

    # Drop every reference so deleting the window drives the teardown above.
    window.close()
    del window, frame, layout, interactor
    gc.collect()
    qapp.processEvents()

    err = capsys.readouterr().err
    assert "already deleted" not in err, err
    assert "Traceback" not in err, err
    dead = weak_interactor()
    # If it outlived the window, the context must at least be forgotten.
    assert dead is None or dead._ctx is None  # noqa: SLF001


def test_depth_peeling(qtbot) -> None:  # noqa: D103
    plotter = BackgroundPlotter()
    qtbot.addWidget(plotter.app_window)
    assert not plotter.renderer.GetUseDepthPeeling()
    plotter.close()
    global_theme.depth_peeling["enabled"] = True
    plotter = BackgroundPlotter(app_window_class=SuperWindow)
    assert isinstance(plotter.app_window, SuperWindow)
    assert isinstance(plotter.app_window, MainWindow)
    qtbot.addWidget(plotter.app_window)
    assert plotter.renderer.GetUseDepthPeeling()
    plotter.close()
    global_theme.depth_peeling["enabled"] = False


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS activation policy")
def test_depth_peeling_probe_keeps_application_regular(qtbot) -> None:
    """
    Probing for depth peeling must not demote this application.

    pyvista answers ``enable_depth_peeling()`` by rendering into a throwaway
    off-screen render window, and on macOS that demotes the process-global
    ``NSApplication`` activation policy away from ``Regular`` so an unbundled
    headless process gets no Dock icon (pyvista#8832). A Qt application is not
    headless: the demotion costs it its Dock icon and menu bar, and the window
    server can stop presenting a window that is already on screen -- drawn
    once and never again, with ``isVisible()`` still ``True``, so nothing ever
    retries the show and only ``hide()``/``show()`` brings it back.

    The policy is what this asserts. The lost window is the symptom worth
    caring about, but it only follows the first ``Regular`` -> ``Accessory``
    transition in a process and not reliably even then, so ``isExposed()``
    is far too weak to hang a test on.
    """
    appkit = pytest.importorskip("AppKit")
    app = appkit.NSApp()
    if app is None:
        pytest.skip("no NSApplication in this process")
    regular = appkit.NSApplicationActivationPolicyRegular
    original = app.activationPolicy()

    plotter = BackgroundPlotter()
    qtbot.addWidget(plotter.app_window)
    try:
        # The policy is sticky and process-global, so an earlier probe in this
        # session may already have demoted it and would mask the assertion
        app.setActivationPolicy_(regular)
        # A warm cache answers without probing at all, and test_depth_peeling
        # warms it; pyvista only began caching in 0.49, hence the getattr
        cache_clear = getattr(check_depth_peeling, "cache_clear", None)
        if cache_clear is not None:
            cache_clear()
        plotter.enable_depth_peeling()
        assert app.activationPolicy() == regular
    finally:
        app.setActivationPolicy_(original)
        plotter.close()


@pytest.mark.skipif(
    platform.system() == "Windows" and API_NAME in ("PySide6", "PyQt6"),
    reason="Can be in offscreen mode on Windows",
)
def test_off_screen(qtbot) -> None:  # noqa: D103
    plotter = BackgroundPlotter(off_screen=False)
    qtbot.addWidget(plotter.app_window)
    assert not plotter.ren_win.GetOffScreenRendering()
    plotter.close()
    plotter = BackgroundPlotter(off_screen=True)
    qtbot.addWidget(plotter.app_window)
    assert plotter.ren_win.GetOffScreenRendering()
    plotter.close()


def test_smoothing(qtbot) -> None:  # noqa: D103
    plotter = BackgroundPlotter()
    qtbot.addWidget(plotter.app_window)
    assert not plotter.ren_win.GetPolygonSmoothing()
    assert not plotter.ren_win.GetLineSmoothing()
    assert not plotter.ren_win.GetPointSmoothing()
    plotter.close()
    plotter = BackgroundPlotter(
        polygon_smoothing=True,
        line_smoothing=True,
        point_smoothing=True,
    )
    qtbot.addWidget(plotter.app_window)
    assert plotter.ren_win.GetPolygonSmoothing()
    assert plotter.ren_win.GetLineSmoothing()
    assert plotter.ren_win.GetPointSmoothing()
    plotter.close()


def test_counter(qtbot) -> None:  # noqa: D103
    with pytest.raises(TypeError, match="type of"):
        Counter(count=0.5)
    with pytest.raises(ValueError, match="strictly positive"):
        Counter(count=-1)

    counter = Counter(count=1)
    assert counter.count == 1
    with qtbot.wait_signals([counter.signal_finished], timeout=1000):
        counter.decrease()
    assert counter.count == 0


@pytest.mark.parametrize("border", [True, False])
def test_subplot_gc(border) -> None:  # noqa: D103
    plotter = BackgroundPlotter(shape=(2, 1), update_app_icon=False, border=border)
    plotter.close()  # TODO: Should automatically close but need it on macOS + PySide6!  # noqa: FIX002, TD002, TD003


def test_editor(qtbot, plotting) -> None:  # noqa: ARG001, D103
    print("test editor=False")
    plotter = BackgroundPlotter(editor=False, off_screen=False)
    assert plotter.editor is None
    plotter.close()

    print("test editor closing")
    plotter = BackgroundPlotter(editor=True, off_screen=False)
    assert_hasattr(plotter, "editor", Editor)
    editor = plotter.editor
    assert not editor.isVisible()
    with wait_exposed(qtbot, editor):
        editor.toggle()
    assert editor.isVisible()
    print("editor close")
    editor.close()
    assert not editor.isVisible()
    print("plotter close")
    plotter.close()

    print("editor=True by default")
    plotter = BackgroundPlotter(shape=(2, 1), off_screen=False)
    editor = plotter.editor
    with wait_exposed(qtbot, editor):
        editor.toggle()

    print("add at least an actor")
    plotter.subplot(0, 0)
    pd = pyvista.Sphere()
    actor = plotter.add_mesh(pd)
    plotter.subplot(1, 0)
    plotter.show_axes()

    assert_hasattr(editor, "tree_widget", QTreeWidget)
    tree_widget = editor.tree_widget
    top_item = tree_widget.topLevelItem(0)  # any renderer will do
    assert top_item is not None

    print("simulate selection")
    with qtbot.wait_signals([tree_widget.itemSelectionChanged], timeout=2000):
        top_item.setSelected(True)

    print("toggle all the renderer-associated checkboxes twice")
    # to ensure that slots are called for True and False
    assert_hasattr(editor, "stacked_widget", QStackedWidget)
    stacked_widget = editor.stacked_widget
    page_idx = top_item.data(0, Qt.ItemDataRole.UserRole)
    page_widget = stacked_widget.widget(page_idx)
    page_layout = page_widget.layout()
    number_of_widgets = page_layout.count()
    for widget_idx in range(number_of_widgets):
        widget_item = page_layout.itemAt(widget_idx)
        widget = widget_item.widget()
        if isinstance(widget, QCheckBox):
            with qtbot.wait_signals([widget.toggled], timeout=2000):
                widget.toggle()
            with qtbot.wait_signals([widget.toggled], timeout=2000):
                widget.toggle()

    print("hide the editor for coverage")
    editor.toggle()
    plotter.remove_actor(actor)
    plotter.close()


@pytest.fixture
def ensure_closed():  # noqa: ANN201
    """Ensure all plotters are closed."""
    try:
        from pyvista.plotting import close_all  # noqa: PLC0415
        from pyvista.plotting.plotter import _ALL_PLOTTERS  # noqa: PLC0415
    except ImportError:  # PV < 0.40
        from pyvista.plotting.plotting import _ALL_PLOTTERS  # noqa: PLC0415
        from pyvista.plotting.plotting import close_all  # noqa: PLC0415
    close_all()  # this is necessary to test _ALL_PLOTTERS
    assert len(_ALL_PLOTTERS) == 0
    yield
    assert len(_ALL_PLOTTERS) == 0


def test_qt_interactor(qtbot, plotting, ensure_closed) -> None:  # noqa: ARG001, D103
    window = TstWindow(show=False, off_screen=False)
    qtbot.addWidget(window)  # register the main widget

    # check that TstWindow.__init__() is called
    assert_hasattr(window, "vtk_widget", QtInteractor)

    vtk_widget = window.vtk_widget  # QtInteractor

    # check that QtInteractor.__init__() is called
    assert hasattr(vtk_widget, "iren")
    assert_hasattr(vtk_widget, "render_timer", QTimer)
    # check that BasePlotter.__init__() is called
    assert_hasattr(vtk_widget, "_closed", bool)
    assert_hasattr(vtk_widget, "renderer", vtk.vtkRenderer)
    # check that QVTKRenderWindowInteractorAdapter.__init__() is called
    assert_hasattr(vtk_widget, "interactor", QVTKRenderWindowInteractor)

    interactor = vtk_widget.interactor  # QVTKRenderWindowInteractor
    render_timer = vtk_widget.render_timer  # QTimer
    renderer = vtk_widget.renderer  # vtkRenderer

    # ensure that self.render is called by the timer
    render_blocker = qtbot.wait_signals([render_timer.timeout], timeout=500)
    render_blocker.wait()

    window.add_sphere()
    assert np.any(window.vtk_widget.mesh.points)

    with wait_exposed(qtbot, window):
        window.show()
    with wait_exposed(qtbot, interactor):
        interactor.show()

    assert window.isVisible()
    assert interactor.isVisible()
    assert render_timer.isActive()
    assert not vtk_widget._closed  # noqa: SLF001

    # test enable/disable interactivity
    vtk_widget.disable()
    assert not renderer.GetInteractive()
    vtk_widget.enable()
    assert renderer.GetInteractive()

    window.close()

    assert not window.isVisible()
    assert not interactor.isVisible()
    assert not render_timer.isActive()

    # check that BasePlotter.close() is called
    assert vtk_widget._closed  # noqa: SLF001


def test_auto_render_skips_hidden_window(qtbot, plotting, ensure_closed) -> None:  # noqa: ARG001
    """
    Auto-update timer must not render a hidden on-screen window (see #762).

    When two ``QtInteractor`` windows share an OpenGL context, letting a closed
    (hidden) window's render timer keep firing renders into an unmapped or
    finalized GL context, which freezes or crashes the *other* window. The
    timer callback must therefore skip rendering while the on-screen widget is
    not visible.
    """
    plotter = BackgroundPlotter(show=False, off_screen=False, update_app_icon=False)
    qtbot.addWidget(plotter.app_window)
    plotter.render_timer.stop()  # drive _auto_render manually and deterministically
    plotter.add_mesh(pyvista.Sphere())

    calls = []
    plotter.render = lambda *args, **kwargs: calls.append(True)  # noqa: ARG005

    # Not shown yet -> not visible -> the timer callback must skip rendering.
    assert not plotter.isVisible()
    plotter._auto_render()  # noqa: SLF001
    assert calls == []

    # Once visible, the timer callback renders normally.
    with wait_exposed(qtbot, plotter.app_window):
        plotter.app_window.show()
    assert plotter.isVisible()
    plotter._auto_render()  # noqa: SLF001
    assert calls == [True]

    plotter.close()


def test_auto_render_offscreen_and_after_close(qtbot, plotting, ensure_closed) -> None:  # noqa: ARG001
    """Off-screen still auto-renders; render() is a no-op after close (#762)."""
    plotter = BackgroundPlotter(show=False, off_screen=True, update_app_icon=False)
    qtbot.addWidget(plotter.app_window)
    plotter.render_timer.stop()  # drive _auto_render manually and deterministically
    plotter.add_mesh(pyvista.Sphere())

    calls = []
    plotter.render = lambda *args, **kwargs: calls.append(True)  # noqa: ARG005
    # Off-screen interactors are never "visible" but must still render.
    assert not plotter.isVisible()
    plotter._auto_render()  # noqa: SLF001
    assert calls == [True]

    # After close, the real render() must be a guarded no-op: the render window
    # has been finalized and touching its GL context can crash.
    del plotter.render  # restore the real, guarded render()
    plotter.close()
    assert plotter._closed  # noqa: SLF001
    plotter.render()  # must not raise


@pytest.mark.parametrize(
    "show_plotter",
    [
        True,
        False,
    ],
)
def test_background_plotting_axes_scale(qtbot, show_plotter, plotting) -> None:  # noqa: ARG001, D103
    plotter = BackgroundPlotter(show=show_plotter, off_screen=False, title="Testing Window")
    assert_hasattr(plotter, "app_window", MainWindow)
    window = plotter.app_window  # MainWindow
    qtbot.addWidget(window)  # register the window

    # show the window
    if not show_plotter:
        assert not window.isVisible()
        with wait_exposed(qtbot, window):
            window.show()
    assert window.isVisible()

    plotter.add_mesh(pyvista.Sphere())
    assert_hasattr(plotter, "renderer", Renderer)
    renderer = plotter.renderer
    assert len(renderer._actors) == 1  # noqa: SLF001
    assert np.any(plotter.mesh.points)

    dlg = plotter.scale_axes_dialog(show=False)  # ScaleAxesDialog
    qtbot.addWidget(dlg)  # register the dialog

    # show the dialog
    assert not dlg.isVisible()
    with wait_exposed(qtbot, dlg):
        dlg.show()
    assert dlg.isVisible()

    value = 2.0
    dlg.x_slider_group.value = value
    assert plotter.scale[0] == value
    dlg.x_slider_group.spinbox.setValue(-1)
    assert dlg.x_slider_group.value == 0
    dlg.x_slider_group.spinbox.setValue(1000.0)
    assert dlg.x_slider_group.value < 100

    plotter._last_update_time = 0.0  # noqa: SLF001
    plotter.update()
    plotter.update_app_icon()
    plotter.close()
    assert not window.isVisible()
    assert not dlg.isVisible()


def test_background_plotting_camera(qtbot, plotting) -> None:  # noqa: ARG001, D103
    plotter = BackgroundPlotter(off_screen=False, title="Testing Window")
    plotter.add_mesh(pyvista.Sphere())

    cpos = [(0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    plotter.camera_position = cpos
    plotter.save_camera_position()
    plotter.camera_position = [(0.0, 0.0, 3.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]

    # load existing position
    # NOTE: 2 because first two (0 and 1) buttons save and clear positions
    plotter.saved_cameras_tool_bar.actions()[2].trigger()
    assert plotter.camera_position == cpos

    plotter.clear_camera_positions()
    # 2 because the first two buttons are save and clear
    assert len(plotter.saved_cameras_tool_bar.actions()) == 2
    plotter.close()


def test_background_plotting_close_gc(qtbot, plotting) -> None:  # noqa: ARG001
    """
    A closed BackgroundPlotter must be garbage-collected.

    Regression test: the toolbars/menu/editor hold closures capturing the
    plotter, kept alive by the app window's Qt objects. ``close()`` schedules
    the window for deletion so those objects (and their closures) go away,
    breaking the cycle. Without that, the plotter leaks.
    """
    plotter = BackgroundPlotter(off_screen=False, title="Testing Window")
    plotter.add_mesh(pyvista.Sphere(), scalars=pyvista.Sphere().points[:, 0])
    plotter.save_camera_position()
    ref = weakref.ref(plotter)
    plotter.close()
    del plotter
    # process the scheduled (deleteLater) deletions, then collect
    for _ in range(3):
        qtbot.wait(10)
        gc.collect()
    assert ref() is None


@pytest.mark.parametrize("other_views", [None, 0, [0]])
def test_link_views_across_plotters(other_views) -> None:  # noqa: D103
    def _to_array(camera_position):  # noqa: ANN202
        return np.asarray([list(row) for row in camera_position])

    plotter_one = BackgroundPlotter(off_screen=True, title="Testing Window")
    plotter_one.add_mesh(pyvista.Sphere())

    plotter_two = BackgroundPlotter(off_screen=True, title="Testing Window")
    plotter_two.add_mesh(pyvista.Sphere())

    plotter_one.link_views_across_plotters(plotter_two, other_views=other_views)

    plotter_one.camera_position = [(0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    np.testing.assert_allclose(
        _to_array(plotter_one.camera_position),
        _to_array(plotter_two.camera_position),
    )

    plotter_two.camera_position = [(0.0, 0.0, 3.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    np.testing.assert_allclose(
        _to_array(plotter_one.camera_position),
        _to_array(plotter_two.camera_position),
    )

    plotter_one.unlink_views()
    plotter_one.camera_position = [(0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]

    with pytest.raises(AssertionError):
        np.testing.assert_allclose(
            _to_array(plotter_one.camera_position),
            _to_array(plotter_two.camera_position),
        )

    match = "Expected `other_views` type is int, or list or tuple of ints, but float64 is given"
    with pytest.raises(TypeError, match=match):
        plotter_one.link_views_across_plotters(plotter_two, other_views=[0.0])


@pytest.mark.parametrize(
    "show_plotter",
    [
        True,
        False,
    ],
)
def test_background_plotter_export_files(qtbot, tmpdir, show_plotter, plotting) -> None:  # noqa: ARG001, D103
    # setup filesystem
    output_dir = str(tmpdir.mkdir("tmpdir"))
    assert os.path.isdir(output_dir)  # noqa: PTH112

    plotter = BackgroundPlotter(show=show_plotter, off_screen=False, title="Testing Window")
    assert_hasattr(plotter, "app_window", MainWindow)
    window = plotter.app_window  # MainWindow
    qtbot.addWidget(window)  # register the window

    # show the window
    if not show_plotter:
        assert not window.isVisible()
        with wait_exposed(qtbot, window):
            window.show()
    assert window.isVisible()

    plotter.add_mesh(pyvista.Sphere())
    assert_hasattr(plotter, "renderer", Renderer)
    renderer = plotter.renderer
    assert len(renderer._actors) == 1  # noqa: SLF001
    assert np.any(plotter.mesh.points)

    dlg = plotter._qt_screenshot(show=False)  # FileDialog  # noqa: SLF001
    qtbot.addWidget(dlg)  # register the dialog

    filename = str(os.path.join(output_dir, "tmp.png"))  # noqa: PTH118
    dlg.selectFile(filename)

    # show the dialog
    assert not dlg.isVisible()
    with wait_exposed(qtbot, dlg):
        dlg.show()
    assert dlg.isVisible()

    # synchronise signal and callback
    if not BAD_INTERACTION:
        with qtbot.wait_signals([dlg.dlg_accepted], timeout=1000):
            dlg.accept()
        assert not dlg.isVisible()  # dialog is closed after accept()
        assert os.path.isfile(filename)  # noqa: PTH113

    plotter.close()
    assert not window.isVisible()


@pytest.fixture(scope="session")
def _trame_server(tmp_path_factory) -> None:
    """
    Launch the process-lifetime trame server outside any GC snapshot.

    The first vtksz export launches a trame server singleton whose helper
    keeps a ``vtkWebApplication`` (and its protocol objects) alive for the
    rest of the process by design; warm it up once so ``check_gc`` does not
    blame those objects on the first exporting test.
    """
    # VTKjs export is only guaranteed on current pyvista + VTK.
    # Older pyvista (< 0.47) still imports the deprecated `nest_asyncio`
    # package and older VTK may lack APIs that trame-vtk relies on.
    pytest.importorskip("pyvista", minversion="0.47")
    pytest.importorskip("vtk", minversion="9.6")
    with contextlib.suppress(ImportError):
        import trame_pyvista  # noqa: F401, PLC0415
    plotter = pyvista.Plotter(off_screen=True)
    plotter.add_mesh(pyvista.Cone())
    trame = getattr(plotter, "trame", None)
    if trame is not None and hasattr(trame, "export_vtksz"):
        trame.export_vtksz(filename=None)  # pyvista >= 0.49 (trame-pyvista)
    else:
        plotter.export_vtksz(str(tmp_path_factory.mktemp("trame") / "warmup.vtksz"))
    plotter.close()


@pytest.fixture
def trame_array_cache(_trame_server, check_gc) -> None:  # noqa: ARG001
    """
    Clear trame's serializer cache before ``check_gc``'s teardown check.

    The (session-lifetime) ``SynchronizationContext`` caches every exported
    data array and only releases them via a 20-second time window, so the
    exporting test's arrays would otherwise survive it.
    """
    yield
    from trame_vtk.modules.vtk import HELPERS_PER_SERVER  # noqa: PLC0415

    for helper in HELPERS_PER_SERVER.values():
        protocol = helper._root_protocol  # noqa: SLF001
        if protocol is None:
            continue
        for link_protocol in protocol.getLinkProtocols():
            context = getattr(link_protocol, "context", None)
            if context is not None:
                context.data_array_cache.clear()


def test_background_plotter_export_vtkjs(qtbot, tmpdir, plotting, trame_array_cache) -> None:  # noqa: ARG001, D103
    # setup filesystem
    output_dir = str(tmpdir.mkdir("tmpdir"))
    assert os.path.isdir(output_dir)  # noqa: PTH112

    plotter = BackgroundPlotter(show=False, off_screen=False, title="Testing Window")
    assert_hasattr(plotter, "app_window", MainWindow)
    window = plotter.app_window  # MainWindow
    qtbot.addWidget(window)  # register the window

    # show the window
    assert not window.isVisible()
    with wait_exposed(qtbot, window):
        window.show()
    assert window.isVisible()

    plotter.add_mesh(pyvista.Sphere())
    assert_hasattr(plotter, "renderer", Renderer)
    renderer = plotter.renderer
    assert len(renderer._actors) == 1  # noqa: SLF001
    assert np.any(plotter.mesh.points)

    dlg = plotter._qt_export_vtkjs(show=False)  # FileDialog  # noqa: SLF001
    qtbot.addWidget(dlg)  # register the dialog

    if hasattr(getattr(plotter, "trame", None), "export_vtksz") or hasattr(plotter, "export_vtksz"):
        ext = ".vtksz"
        filename = str(os.path.join(output_dir, f"tmp{ext}"))  # noqa: PTH118
    else:
        ext = ".vtkjs"
        filename = str(os.path.join(output_dir, "tmp"))  # noqa: PTH118
    dlg.selectFile(filename)

    # show the dialog
    assert not dlg.isVisible()
    with wait_exposed(qtbot, dlg):
        dlg.show()
    assert dlg.isVisible()

    # synchronise signal and callback
    if not BAD_INTERACTION:
        with qtbot.wait_signals([dlg.dlg_accepted], timeout=1000):
            dlg.accept()
        assert not dlg.isVisible()  # dialog is closed after accept()

    plotter.close()
    assert not window.isVisible()

    if ext == ".vtksz":
        assert os.path.isfile(filename)  # noqa: PTH113
    else:
        assert os.path.isfile(filename + ext)  # noqa: PTH113


def test_background_plotting_orbit(qtbot, plotting) -> None:  # noqa: ARG001, D103
    plotter = BackgroundPlotter(off_screen=False, title="Testing Window")
    plotter.add_mesh(pyvista.Sphere())
    # perform the orbit:
    threads_before = set(threading.enumerate())
    plotter.orbit_on_path(threaded=True, step=0.0)
    plotter.close()
    # Released pyvista's threaded orbit is fire-and-forget and close() does
    # not stop it (pyvista#8804 does); on macOS every render() also spawns a
    # thread. A still-running thread's frame holds the plotter, tripping
    # check_gc on runners slow enough for the orbit to outlive the test
    # (macOS Intel), so wait (best effort) for the threads the orbit spawned.
    for thread in set(threading.enumerate()) - threads_before:
        # Only pyvista's render/orbit worker threads (plain Thread) can hold
        # the plotter; a stray stdlib threading.Timer from test infrastructure
        # never does and may outlive the wait, so skip it.
        if isinstance(thread, threading.Timer):
            continue
        # A thread can be enumerated before it is joinable (threading._limbo:
        # start() still in progress on another thread), where join() raises
        # "cannot join thread before it is started" -- seen on Windows. That
        # window is short, so retry rather than give the join up entirely.
        for _ in range(100):
            try:
                thread.join(timeout=10)
            except RuntimeError:  # noqa: PERF203
                time.sleep(0.01)
            else:
                break


@pytest.mark.skipif(sys.version_info < (3, 10), reason="#508")
def test_background_plotting_toolbar(qtbot, plotting) -> None:  # noqa: ARG001, D103
    with pytest.raises(TypeError, match="toolbar"):  # noqa: PT012
        p = BackgroundPlotter(off_screen=False, toolbar="foo")
        p.close()

    plotter = BackgroundPlotter(off_screen=False, toolbar=False)
    assert plotter.default_camera_tool_bar is None
    assert plotter.saved_camera_positions is None
    assert plotter.saved_cameras_tool_bar is None
    plotter.close()

    plotter = BackgroundPlotter(off_screen=False)

    assert_hasattr(plotter, "app_window", MainWindow)
    assert_hasattr(plotter, "default_camera_tool_bar", QToolBar)
    assert_hasattr(plotter, "saved_camera_positions", list)
    assert_hasattr(plotter, "saved_cameras_tool_bar", QToolBar)

    window = plotter.app_window
    default_camera_tool_bar = plotter.default_camera_tool_bar
    saved_cameras_tool_bar = plotter.saved_cameras_tool_bar

    with wait_exposed(qtbot, window):
        window.show()

    assert default_camera_tool_bar.isVisible()
    assert saved_cameras_tool_bar.isVisible()

    # triggering a view action
    plotter._view_action.trigger()  # noqa: SLF001

    plotter.close()


@pytest.mark.skipif(platform.system() == "Windows", reason="Segfaults on Windows")
def test_background_plotting_menu_bar(qtbot, plotting) -> None:  # noqa: ARG001, D103
    print("Bad call")
    with pytest.raises(TypeError, match="menu_bar"):
        BackgroundPlotter(off_screen=False, menu_bar="foo")

    print("Defaults")
    plotter = BackgroundPlotter(off_screen=False, menu_bar=False, update_app_icon=False)
    assert plotter.main_menu is None
    assert plotter._menu_close_action is None  # noqa: SLF001
    plotter.close()

    # menu_bar=True  # noqa: ERA001
    plotter = BackgroundPlotter(off_screen=False, update_app_icon=False)

    assert_hasattr(plotter, "app_window", MainWindow)
    assert_hasattr(plotter, "main_menu", QMenuBar)
    assert_hasattr(plotter, "_menu_close_action", QAction)
    assert_hasattr(plotter, "_edl_action", QAction)
    assert_hasattr(plotter, "_parallel_projection_action", QAction)

    window = plotter.app_window
    main_menu = plotter.main_menu
    assert not main_menu.isNativeMenuBar()

    with wait_exposed(qtbot, window):
        window.show()

    print("EDL action")
    if hasattr(plotter.renderer, "_render_passes"):
        obj, attr = plotter.renderer._render_passes, "_edl_pass"  # noqa: SLF001
    else:
        obj, attr = plotter.renderer, "edl_pass"
    assert getattr(obj, attr, None) is None
    plotter._edl_action.trigger()  # noqa: SLF001
    assert getattr(obj, attr, None) is not None
    # and now test reset
    plotter._edl_action.trigger()  # noqa: SLF001

    print("Parallel projection action")
    assert not plotter.camera.GetParallelProjection()
    plotter._parallel_projection_action.trigger()  # noqa: SLF001
    assert plotter.camera.GetParallelProjection()
    # and now test reset
    plotter._parallel_projection_action.trigger()  # noqa: SLF001

    assert main_menu.isVisible()
    plotter.close()
    assert not main_menu.isVisible()
    assert plotter._last_update_time == -np.inf  # noqa: SLF001


def test_drop_event(tmpdir, qtbot) -> None:  # noqa: D103
    output_dir = str(tmpdir.mkdir("tmpdir"))
    filename = str(os.path.join(output_dir, "tmp.vtk"))  # noqa: PTH118
    mesh = pyvista.Cone()
    mesh.save(filename)
    assert os.path.isfile(filename)  # noqa: PTH113
    plotter = BackgroundPlotter(update_app_icon=False)
    with wait_exposed(qtbot, plotter.app_window):
        plotter.app_window.show()
    point = QPointF(0, 0)
    data = QMimeData()
    data.setUrls([QUrl(filename)])
    event = QDropEvent(
        point,
        Qt.DropAction.IgnoreAction,
        data,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    plotter.dropEvent(event)
    plotter.close()


def test_drag_event(tmpdir) -> None:  # noqa: D103
    output_dir = str(tmpdir.mkdir("tmpdir"))
    filename = str(os.path.join(output_dir, "tmp.vtk"))  # noqa: PTH118
    mesh = pyvista.Cone()
    mesh.save(filename)
    assert os.path.isfile(filename)  # noqa: PTH113
    plotter = BackgroundPlotter(update_app_icon=False)
    point = QPoint(0, 0)
    data = QMimeData()
    data.setUrls([QUrl(filename)])
    event = QDragEnterEvent(
        point,
        Qt.DropAction.IgnoreAction,
        data,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    plotter.dragEnterEvent(event)
    plotter.close()


def test_gesture_event(qtbot) -> None:  # noqa: D103
    plotter = BackgroundPlotter(update_app_icon=False)
    with wait_exposed(qtbot, plotter.app_window):
        plotter.app_window.show()
    gestures = [QPinchGesture()]
    event = QGestureEvent(gestures)
    plotter.gesture_event(event)
    plotter.close()


def test_background_plotting_add_callback(qtbot, monkeypatch, plotting) -> None:  # noqa: ARG001, D103
    class CallBack:
        def __init__(self, sphere) -> None:
            self.sphere = weakref.ref(sphere)

        def __call__(self):  # noqa: ANN204
            self.sphere().points[:] = self.sphere().points * 0.5

    update_count = [0]
    orig_update_app_icon = BackgroundPlotter.update_app_icon

    def update_app_icon(slf):  # noqa: ANN202
        update_count[0] = update_count[0] + 1
        return orig_update_app_icon(slf)

    monkeypatch.setattr(BackgroundPlotter, "update_app_icon", update_app_icon)
    print("Init")
    plotter = BackgroundPlotter(
        show=False,
        off_screen=False,
        title="Testing Window",
        update_app_icon=True,  # also does add_callback
    )
    assert_hasattr(plotter, "app_window", MainWindow)
    assert_hasattr(plotter, "_callback_timer", QTimer)
    assert_hasattr(plotter, "counters", list)
    assert plotter._last_update_time == -np.inf  # noqa: SLF001

    print("Sphere")
    sphere = pyvista.Sphere()
    plotter.add_mesh(sphere)
    mycallback = CallBack(sphere)
    window = plotter.app_window  # MainWindow
    callback_timer = plotter._callback_timer  # QTimer  # noqa: SLF001
    assert callback_timer.isActive()

    print("ensure that the window is shown")
    assert not window.isVisible()
    with wait_exposed(qtbot, window):
        window.show()
    assert window.isVisible()
    # Showing the window can take several seconds on slow CI VMs (macOS
    # runners especially), during which the 1 s callback timer keeps calling
    # update_app_icon -- the absolute call count up to here is
    # timing-dependent. Stop the timer and assert on deltas instead.
    callback_timer.stop()
    base_count = update_count[0]
    # don't check _last_update_time for non-inf-ness, won't be updated on Win
    plotter.update_app_icon()  # the timer doesn't call it right away, so do it
    assert update_count[0] == base_count + 1
    plotter.update_app_icon()  # internally a rate-limited no-op, but still called
    assert update_count[0] == base_count + 2
    with pytest.raises(ValueError, match="ndarray with shape"):
        plotter.set_icon(0.0)
    # Maybe someday manually setting "set_icon" should disable update_app_icon?
    # Strings also supported directly by QIcon
    plotter.set_icon(os.path.join(os.path.dirname(pyvistaqt.__file__), "data", "pyvista_logo_square.png"))  # noqa: PTH118, PTH120
    callback_timer.stop()
    assert not callback_timer.isActive()

    print("check that timers are set properly in add_callback()")
    plotter.add_callback(mycallback, interval=200, count=3)
    callback_timer = plotter._callback_timer  # QTimer  # noqa: SLF001
    assert callback_timer.isActive()
    counter = plotter.counters[-1]  # Counter

    if not BAD_INTERACTION:
        # Generous timeouts: 3 ticks of the 200 ms timer nominally take 600 ms
        # but slow CI VMs (macOS runners especially) can stall the event loop
        # for seconds at a time.
        print("ensure that self.callback_timer send a signal")
        with qtbot.wait_signals([callback_timer.timeout], timeout=10000):
            pass
        print("ensure that self.counters send a signal")
        if counter.count > 0:  # signal_finished may have fired during the wait above
            with qtbot.wait_signals([counter.signal_finished], timeout=10000):
                pass
        assert not callback_timer.isActive()  # counter stops the callback

    plotter.add_callback(mycallback, interval=200)
    callback_timer = plotter._callback_timer  # QTimer  # noqa: SLF001
    assert callback_timer.isActive()

    if not BAD_INTERACTION:
        print("ensure that self.callback_timer send a signal")
        with qtbot.wait_signals([callback_timer.timeout], timeout=10000):
            pass

    plotter.close()
    assert not callback_timer.isActive()  # window stops the callback


@pytest.mark.slow
@pytest.mark.parametrize(
    "close_event",
    [
        "plotter_close",
        "window_close",
        pytest.param("q_key_press"),
        "menu_exit",
        "del_finalizer",
    ],
)
@pytest.mark.parametrize(
    "empty_scene",
    [
        True,
        False,
    ],
)
def test_background_plotting_close(qtbot, close_event, empty_scene, plotting, ensure_closed) -> None:  # noqa: ARG001, D103
    plotter = _create_testing_scene(empty_scene)

    # check that BackgroundPlotter.__init__() is called
    assert_hasattr(plotter, "app_window", MainWindow)
    assert_hasattr(plotter, "main_menu", QMenuBar)
    # check that QtInteractor.__init__() is called
    assert hasattr(plotter, "iren")
    assert_hasattr(plotter, "render_timer", QTimer)
    # check that BasePlotter.__init__() is called
    assert_hasattr(plotter, "_closed", bool)
    # check that QVTKRenderWindowInteractorAdapter._init__() is called
    assert_hasattr(plotter, "interactor", QVTKRenderWindowInteractor)

    window = plotter.app_window  # MainWindow
    main_menu = plotter.main_menu
    assert not main_menu.isNativeMenuBar()
    interactor = plotter.interactor  # QVTKRenderWindowInteractor
    render_timer = plotter.render_timer  # QTimer

    qtbot.addWidget(window)  # register the main widget

    # ensure that self.render is called by the timer
    render_blocker = qtbot.wait_signals([render_timer.timeout], timeout=500)
    render_blocker.wait()

    # ensure that the widgets are showed
    with wait_exposed(qtbot, window):
        window.show()
    with wait_exposed(qtbot, interactor):
        interactor.show()

    # check that the widgets are showed properly
    assert window.isVisible()
    assert interactor.isVisible()
    assert main_menu.isVisible()
    assert render_timer.isActive()
    assert not plotter._closed  # noqa: SLF001

    with qtbot.wait_signals([window.signal_close], timeout=500):
        if close_event == "plotter_close":
            plotter.close()
        elif close_event == "window_close":
            window.close()
        elif close_event == "q_key_press":
            qtbot.keyClick(interactor, "q")
        elif close_event == "menu_exit":
            plotter._menu_close_action.trigger()  # noqa: SLF001
        elif close_event == "del_finalizer":
            plotter.__del__()

    # check that the widgets are closed
    assert not window.isVisible()
    assert not interactor.isVisible()
    assert not main_menu.isVisible()
    assert not render_timer.isActive()

    # check that BasePlotter.close() is called
    assert plotter._closed  # noqa: SLF001


def test_multiplotter(qtbot, plotting) -> None:  # noqa: ARG001, D103
    with pytest.warns(FutureWarning, match="MultiPlotter is deprecated"):
        mp = MultiPlotter(
            nrows=1,
            ncols=2,
            window_size=(300, 300),
            show=False,
            title="Test",
            off_screen=False,
        )
    qtbot.addWidget(mp._window)  # noqa: SLF001
    mp[0, 0].add_mesh(pyvista.Cone())
    mp[0, 1].add_mesh(pyvista.Box())
    assert not mp._window.isVisible()  # noqa: SLF001
    with wait_exposed(qtbot, mp._window):  # noqa: SLF001
        mp.show()
    assert mp._window.isVisible()  # noqa: SLF001
    for p in mp._plotters:  # noqa: SLF001
        assert not p._closed  # noqa: SLF001
    with qtbot.wait_signals([mp._window.signal_close], timeout=1000):  # noqa: SLF001
        mp.close()
    for p in mp._plotters:  # noqa: SLF001
        assert p._closed  # noqa: SLF001

    # cover default show=True
    with pytest.warns(FutureWarning, match="MultiPlotter is deprecated"):
        mp = MultiPlotter(off_screen=False, menu_bar=False, toolbar=False)
    qtbot.addWidget(mp._window)  # noqa: SLF001
    with wait_exposed(qtbot, mp._window):  # noqa: SLF001
        assert mp._window.isVisible()  # noqa: SLF001
    mp.close()


def _create_testing_scene(empty_scene, show=False, off_screen=False):  # noqa: ANN202, FBT002
    if empty_scene:
        plotter = BackgroundPlotter(
            show=show,
            off_screen=off_screen,
            update_app_icon=False,
        )
    else:
        plotter = BackgroundPlotter(
            shape=(2, 2),
            border=True,
            border_width=10,
            border_color="grey",
            show=show,
            off_screen=off_screen,
            update_app_icon=False,
        )
        plotter.set_background("black", top="blue")
        plotter.subplot(0, 0)
        cone = pyvista.Cone(resolution=4)
        actor = plotter.add_mesh(cone)
        plotter.remove_actor(actor)
        plotter.add_text("Actor is removed")
        plotter.subplot(0, 1)
        plotter.add_mesh(pyvista.Box(), color="green", opacity=0.8)
        plotter.subplot(1, 0)
        cylinder = pyvista.Cylinder(resolution=6)
        plotter.add_mesh(cylinder, smooth_shading=True)
        plotter.show_bounds()
        plotter.subplot(1, 1)
        sphere = pyvista.Sphere(phi_resolution=6, theta_resolution=6)
        plotter.add_mesh(sphere)
        plotter.enable_cell_picking()
    return plotter


def assert_hasattr(variable, attribute_name, variable_type) -> None:  # noqa: D103
    __tracebackhide__ = True
    assert hasattr(variable, attribute_name)
    assert isinstance(getattr(variable, attribute_name), variable_type)


@pytest.mark.parametrize("n_win", [1, 2])
def test_sphinx_gallery_scraping(qtbot, monkeypatch, plotting, tmpdir, n_win) -> None:  # noqa: ARG001, D103
    pytest.importorskip("sphinx_gallery")
    if BAD_INTERACTION:
        pytest.skip("Test freezes with BAD_INTERACTION")
    if n_win == 2 and API_NAME == "PySide6" and sys.platform == "linux":
        pytest.skip("Problems with PySide6 with multiple windows")
    if n_win == 2 and sys.platform == "win32":
        pytest.skip("Problems on Windows with multiple windows")
    monkeypatch.setattr(pyvista, "BUILDING_GALLERY", True)

    print(f"Initialize {n_win} plotter(s)")
    plotters = [BackgroundPlotter(off_screen=False, editor=False, show=True) for _ in range(n_win)]

    # Adapted from pyvista/tests/test_scraper.py
    print("Initialize scraper")
    scraper = Scraper()
    src_dir = str(tmpdir)
    out_dir = op.join(str(tmpdir), "_build", "html")  # noqa: PTH118
    img_fnames = [op.join(src_dir, "auto_examples", "images", f"sg_img_{n}.png") for n in range(n_win)]  # noqa: PTH118
    gallery_conf = {"src_dir": src_dir, "builder_name": "html"}
    target_file = op.join(src_dir, "auto_examples", "sg.py")  # noqa: PTH118
    block = None
    block_vars = {
        "image_path_iterator": (img for img in img_fnames),
        "example_globals": {"a": 1},
        "target_file": target_file,
    }
    os.makedirs(op.dirname(img_fnames[0]))  # noqa: PTH103, PTH120
    for img_fname in img_fnames:
        assert not os.path.isfile(img_fname)  # noqa: PTH113
    os.makedirs(out_dir)  # noqa: PTH103
    print("Scraping")
    scraper(block, block_vars, gallery_conf)
    for img_fname in img_fnames:
        assert os.path.isfile(img_fname)  # noqa: PTH113
    print("Closing")
    for plotter in plotters:
        plotter.close()


_skip_darwin_intel = pytest.mark.skipif(
    sys.platform == "darwin" and platform.machine() == "x86_64",
    reason="Takes ~3 minutes per param on macOS Intel CI runners",
)


@pytest.mark.slow
@pytest.mark.parametrize(
    "aa",
    [
        pytest.param(False, marks=_skip_darwin_intel),
        "fxaa",
        pytest.param("msaa", marks=_skip_darwin_intel),
        # TODO: SSAA renders correctly now (xpasses), but a ref cycle in  # noqa: FIX002, TD002, TD003
        # PyVista keeps VTK objects alive and fails the GC check on some CI
        # configurations (the xfail also covers that teardown error).
        pytest.param(
            "ssaa",
            marks=pytest.mark.xfail(reason="ref cycle in PyVista prevents GC", strict=False),
        ),
    ],
)
def test_background_plotting_plots(qtbot, plotting, ensure_closed, aa) -> None:  # noqa: ARG001, C901, D103, PLR0912
    print("Init")
    plotter = BackgroundPlotter(
        show=True,
        off_screen=False,
        shape=(2, 2),
        border=False,
        auto_update=False,
        menu_bar=False,
        toolbar=False,
        update_app_icon=False,
    )
    print("Check skips")
    # Realizes the GL context, which the expose below otherwise waits on
    print("Ren window capabilities")
    gpu_info_full = plotter.ren_win.ReportCapabilities()
    skip_reason = None
    if aa == "fxaa":  # Breaks on Windows and mesa
        if platform.system() == "Windows":
            skip_reason = "FXAA segfaults Windows"
        else:
            # Check if Mesa
            gpu_info = re.findall("OpenGL version string:(.+)\n", gpu_info_full)
            gpu_info = " ".join(gpu_info).lower()
            is_mesa = "mesa" in gpu_info.split()
            if is_mesa:
                skip_reason = "FXAA broken on Mesa"
    if skip_reason:
        print("Skipping test")
        plotter.close()
        pytest.skip(skip_reason)
    print("Background")
    plotter.set_background("black")
    cone = pyvista.Cone(resolution=4)
    for ri in range(2):
        for ci in range(2):
            plotter.subplot(ri, ci)
            plotter.add_mesh(cone)
            plotter.camera.zoom(3)  # 5 magnifies so far that macOS software rendering drops parts of the cone
            if aa:
                print("Enabling AA")
                plotter.enable_anti_aliasing(aa_type=aa)
    print("Waiting")
    with wait_exposed(qtbot, plotter):
        plotter.window().show()
    if sys.platform == "darwin":
        # On macOS >= 26, Qt >= 6.10 disables OpenGL process-wide when the GL
        # context would use the Apple *software* renderer (qtbase a9ca1aef2291:
        # NSOpenGLContext crashes; GitHub Actions arm64 VMs hit this), so the
        # QOpenGLWidget never gets a GL context and nothing can render. Where a
        # software context is still handed out (e.g. Qt 6.11 on the same VMs,
        # or older macOS), the arm64 software renderer draws with a corrupted
        # view transform. Either way no meaningful pixel assertion is possible.
        skip_reason = None
        if plotter.interactor._ctx is None:  # noqa: SLF001
            skip_reason = "Qt did not provide a GL context (macOS software GL)"
        elif platform.machine() == "arm64" and "Apple Software Renderer" in plotter.ren_win.ReportCapabilities():
            skip_reason = "Apple software GL renders a corrupted view on arm64"
        if skip_reason:
            plotter.close()
            pytest.skip(skip_reason)
    # `image` grabs the buffer as-is, and `plotter.render()` is threaded on Darwin, so draw synchronously
    plotter.ren_win.Render()
    img = np.array(plotter.image)
    drawn = img.any(-1)
    del img
    print(f"Drawn {drawn.mean():.3f}")
    if not BAD_INTERACTION:
        # The cone covers 0.63 of the frame at this zoom on every platform measured
        assert 0.55 < drawn.mean() < 0.70
    plotter.close()


def test_make_current_from_worker_thread(qtbot) -> None:
    """A cross-thread MakeCurrent must not abort the process (invariant 6)."""
    from qtpy.QtGui import QOpenGLContext  # noqa: PLC0415

    plotter = BackgroundPlotter()
    qtbot.addWidget(plotter.app_window)
    with wait_exposed(qtbot, plotter.app_window):
        plotter.app_window.show()

    # Call the observer rather than ren_win.MakeCurrent(): VTK's event dispatch
    # is not thread-safe, so going through it races whatever the GUI thread is
    # doing and access-violates on Windows for reasons the guard cannot fix.
    # This is the function the guard lives in, and the only part of a render
    # this widget owns. Without the guard Qt aborts the whole run here rather
    # than failing this test.
    interactor = plotter.interactor
    errors: list[BaseException] = []
    current: list[bool] = []

    def worker() -> None:
        try:
            interactor._cb_make_current(None, None)  # noqa: SLF001
            current.append(QOpenGLContext.currentContext() is not None)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    # Deliberately not qtbot.waitUntil: that pumps the event loop, which lets
    # the GUI thread render while the worker is inside the observer.
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert not errors
    assert current == [False]  # skipped, rather than made current off-thread
    plotter.close()


@pytest.mark.parametrize(
    ("env", "platform_name", "expected"),
    [
        # The bug: a Wayland session with Qt forced through XWayland, so
        # pyvista would probe with an EGL render window in a GLX process.
        ({"WAYLAND_DISPLAY": "wayland-0"}, "xcb", "vtkXOpenGLRenderWindow"),
        # Native Wayland: pyvista's guess is already EGL, and saying so here
        # would also flip uses_egl() and downgrade FXAA to SSAA.
        ({"WAYLAND_DISPLAY": "wayland-0"}, "wayland", None),
        # No compositor: pyvista never reaches for EGL, nothing to correct.
        ({}, "xcb", None),
        # An explicit choice outranks ours.
        (
            {"WAYLAND_DISPLAY": "wayland-0", "VTK_DEFAULT_OPENGL_WINDOW": "vtkEGLRenderWindow"},
            "xcb",
            None,
        ),
        # Neither offscreen nor minimal implies GLX.
        ({"WAYLAND_DISPLAY": "wayland-0"}, "offscreen", None),
    ],
)
def test_gl_backend_for(monkeypatch, env, platform_name, expected) -> None:
    """Only a Wayland session that Qt did not join gets its backend corrected."""
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("VTK_DEFAULT_OPENGL_WINDOW", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert _gl_backend_for(platform_name) == expected


def test_declared_gl_backend_is_scoped(qapp, monkeypatch) -> None:
    """The declaration is borrowed for the probe, never left behind."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("VTK_DEFAULT_OPENGL_WINDOW", raising=False)
    inside = []
    with _declared_gl_backend():
        inside.append(os.environ.get("VTK_DEFAULT_OPENGL_WINDOW"))
    assert "VTK_DEFAULT_OPENGL_WINDOW" not in os.environ
    # xcb is the only platform that gets a declaration; anything else is a
    # no-op, and this suite runs under both
    platform_name = qapp.platformName()
    expected = "vtkXOpenGLRenderWindow" if platform_name.startswith("xcb") else None
    assert inside == [expected]


def test_declared_gl_backend_restores_on_error(qapp, monkeypatch) -> None:  # noqa: ARG001
    """A failing probe must not leak the declaration either."""
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("VTK_DEFAULT_OPENGL_WINDOW", raising=False)
    msg = "boom"
    with pytest.raises(RuntimeError, match=msg), _declared_gl_backend():
        raise RuntimeError(msg)
    assert "VTK_DEFAULT_OPENGL_WINDOW" not in os.environ
