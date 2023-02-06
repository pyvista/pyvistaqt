import os
import os.path as op
from packaging.version import Version
import platform
import weakref

import numpy as np
import pytest
import pyvista
import vtk
from qtpy.QtWidgets import QAction, QFrame, QMenuBar, QToolBar, QVBoxLayout
from qtpy import QtCore
from qtpy.QtCore import Qt, QPoint, QPointF, QMimeData, QUrl
from qtpy.QtGui import QDragEnterEvent, QDropEvent
from qtpy.QtWidgets import (QTreeWidget, QStackedWidget, QCheckBox,
                            QGestureEvent, QPinchGesture)
from pyvistaqt.plotting import global_theme
from pyvista.plotting import Renderer
from pyvista.utilities import Scraper

import pyvistaqt
from pyvistaqt import MultiPlotter, BackgroundPlotter, MainWindow, QtInteractor
from pyvistaqt.plotting import Counter, QTimer, QVTKRenderWindowInteractor
from pyvistaqt.editor import Editor
from pyvistaqt.dialog import FileDialog
from pyvistaqt.utils import _setup_application, _create_menu_bar, _check_type


WANT_AFTER = 0 if Version(pyvista.__version__) >= Version('0.37') else 1


class TstWindow(MainWindow):
    def __init__(self, parent=None, show=True, off_screen=True):
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

        mainMenu = _create_menu_bar(parent=self)

        fileMenu = mainMenu.addMenu('File')
        self.exit_action = QAction('Exit', self)
        self.exit_action.setShortcut('Ctrl+Q')
        self.exit_action.triggered.connect(self.close)
        fileMenu.addAction(self.exit_action)

        meshMenu = mainMenu.addMenu('Mesh')
        self.add_sphere_action = QAction('Add Sphere', self)
        self.exit_action.setShortcut('Ctrl+A')
        self.add_sphere_action.triggered.connect(self.add_sphere)
        meshMenu.addAction(self.add_sphere_action)

        self.signal_close.connect(self.vtk_widget.close)

        if show:
            self.show()

    def add_sphere(self):
        sphere = pyvista.Sphere(
            phi_resolution=6,
            theta_resolution=6
        )
        self.vtk_widget.add_mesh(sphere)
        self.vtk_widget.reset_camera()


def test_create_menu_bar(qtbot):
    menu_bar = _create_menu_bar(parent=None)
    qtbot.addWidget(menu_bar)


def test_setup_application(qapp):
    _setup_application(qapp)


def test_file_dialog(tmpdir, qtbot):
    dialog = FileDialog(
        filefilter=None,
        directory=False,
        save_mode=False,
        show=False,
    )
    qtbot.addWidget(dialog)

    dialog.emit_accepted()  # test no result

    p = tmpdir.mkdir("tmp").join("foo.png")
    p.write('foo')
    assert os.path.isfile(p)

    filename = str(p)
    dialog.selectFile(filename)

    # show the dialog
    assert not dialog.isVisible()
    with qtbot.wait_exposed(dialog):
        dialog.show()
    assert dialog.isVisible()

    # synchronise signal and callback
    with qtbot.wait_signals([dialog.dlg_accepted], timeout=1000):
        dialog.accept()
    assert not dialog.isVisible()  # dialog is closed after accept()


def test_check_type():
    with pytest.raises(TypeError, match="Expected type"):
        _check_type(0, "foo", [str])
    _check_type(0, "foo", [int, float])
    _check_type("foo", "foo", [str])


def test_mouse_interactions(qtbot):
    plotter = BackgroundPlotter()
    window = plotter.app_window
    interactor = plotter.interactor
    qtbot.addWidget(window)
    point = QPoint(0, 0)
    qtbot.mouseMove(interactor, point)
    qtbot.mouseClick(interactor, QtCore.Qt.LeftButton)
    plotter.close()


@pytest.mark.skipif(platform.system()=="Windows" and platform.python_version()[:-1]=="3.8.", reason="#51")
def test_ipython(qapp):
    IPython = pytest.importorskip('IPython')
    cmd = "from pyvistaqt import BackgroundPlotter as Plotter;" \
          "p = Plotter(show=False, off_screen=False); p.close(); exit()"
    IPython.start_ipython(argv=["-c", cmd])


class SuperWindow(MainWindow):
    pass


def test_depth_peeling(qtbot):
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


def test_off_screen(qtbot):
    plotter = BackgroundPlotter(off_screen=False)
    qtbot.addWidget(plotter.app_window)
    assert not plotter.ren_win.GetOffScreenRendering()
    plotter.close()
    plotter = BackgroundPlotter(off_screen=True)
    qtbot.addWidget(plotter.app_window)
    assert plotter.ren_win.GetOffScreenRendering()
    plotter.close()


def test_smoothing(qtbot):
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


def test_counter(qtbot):
    with pytest.raises(TypeError, match='type of'):
        Counter(count=0.5)
    with pytest.raises(ValueError, match='strictly positive'):
        Counter(count=-1)

    counter = Counter(count=1)
    assert counter.count == 1
    with qtbot.wait_signals([counter.signal_finished], timeout=1000):
        counter.decrease()
    assert counter.count == 0


# TODO: Fix gc on PySide6
@pytest.mark.parametrize('border', (True, False))
@pytest.mark.allow_bad_gc_pyside
def test_subplot_gc(border):
    BackgroundPlotter(shape=(2, 1), update_app_icon=False, border=border)


@pytest.mark.allow_bad_gc_pyside
def test_editor(qtbot, plotting):
    # test editor=False
    plotter = BackgroundPlotter(editor=False, off_screen=False)
    qtbot.addWidget(plotter.app_window)
    assert plotter.editor is None
    plotter.close()

    # test editor closing
    plotter = BackgroundPlotter(editor=True, off_screen=False)
    qtbot.addWidget(plotter.app_window)
    assert_hasattr(plotter, "editor", Editor)
    editor = plotter.editor
    assert not editor.isVisible()
    with qtbot.wait_exposed(editor):
        editor.toggle()
    assert editor.isVisible()
    editor.close()
    assert not editor.isVisible()
    plotter.close()

    # editor=True by default
    plotter = BackgroundPlotter(shape=(2, 1), off_screen=False)
    qtbot.addWidget(plotter.app_window)
    editor = plotter.editor
    with qtbot.wait_exposed(editor):
        editor.toggle()

    # add at least an actor
    plotter.subplot(0, 0)
    pd = pyvista.Sphere()
    actor = plotter.add_mesh(pd)
    plotter.subplot(1, 0)
    plotter.show_axes()

    assert_hasattr(editor, "tree_widget", QTreeWidget)
    tree_widget = editor.tree_widget
    top_item = tree_widget.topLevelItem(0)  # any renderer will do
    assert top_item is not None

    # simulate selection
    with qtbot.wait_signals([tree_widget.itemSelectionChanged], timeout=2000):
        top_item.setSelected(True)

    # toggle all the renderer-associated checkboxes twice
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

    # hide the editor for coverage
    editor.toggle()
    plotter.remove_actor(actor)
    plotter.close()


def test_qt_interactor(qtbot, plotting):
    from pyvista.plotting.plotting import _ALL_PLOTTERS, close_all
    close_all()  # this is necessary to test _ALL_PLOTTERS
    assert len(_ALL_PLOTTERS) == 0

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

    with qtbot.wait_exposed(window):
        window.show()
    with qtbot.wait_exposed(interactor):
        interactor.show()

    assert window.isVisible()
    assert interactor.isVisible()
    assert render_timer.isActive()
    assert not vtk_widget._closed

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
    if Version(pyvista.__version__) < Version('0.27.0'):
        assert not hasattr(vtk_widget, "iren")
    assert vtk_widget._closed

    assert len(_ALL_PLOTTERS) == WANT_AFTER


@pytest.mark.parametrize('show_plotter', [
    True,
    False,
    ])
def test_background_plotting_axes_scale(qtbot, show_plotter, plotting):
    plotter = BackgroundPlotter(
        show=show_plotter,
        off_screen=False,
        title='Testing Window'
    )
    assert_hasattr(plotter, "app_window", MainWindow)
    window = plotter.app_window  # MainWindow
    qtbot.addWidget(window)  # register the window

    # show the window
    if not show_plotter:
        assert not window.isVisible()
        with qtbot.wait_exposed(window):
            window.show()
    assert window.isVisible()

    plotter.add_mesh(pyvista.Sphere())
    assert_hasattr(plotter, "renderer", Renderer)
    renderer = plotter.renderer
    assert len(renderer._actors) == 1
    assert np.any(plotter.mesh.points)

    dlg = plotter.scale_axes_dialog(show=False)  # ScaleAxesDialog
    qtbot.addWidget(dlg)  # register the dialog

    # show the dialog
    assert not dlg.isVisible()
    with qtbot.wait_exposed(dlg):
        dlg.show()
    assert dlg.isVisible()

    value = 2.0
    dlg.x_slider_group.value = value
    assert plotter.scale[0] == value
    dlg.x_slider_group.spinbox.setValue(-1)
    assert dlg.x_slider_group.value == 0
    dlg.x_slider_group.spinbox.setValue(1000.0)
    assert dlg.x_slider_group.value < 100

    plotter._last_update_time = 0.0
    plotter.update()
    plotter.update_app_icon()
    plotter.close()
    assert not window.isVisible()
    assert not dlg.isVisible()


def test_background_plotting_camera(qtbot, plotting):
    plotter = BackgroundPlotter(off_screen=False, title='Testing Window')
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


@pytest.mark.parametrize('other_views', [None, 0, [0]])
def test_link_views_across_plotters(other_views):

    def _to_array(camera_position):
        return np.asarray([list(row) for row in camera_position])

    plotter_one = BackgroundPlotter(off_screen=True, title='Testing Window')
    plotter_one.add_mesh(pyvista.Sphere())

    plotter_two = BackgroundPlotter(off_screen=True, title='Testing Window')
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

    match = 'Expected `other_views` type is int, or list or tuple of ints, but float64 is given'
    with pytest.raises(TypeError, match=match):
        plotter_one.link_views_across_plotters(plotter_two, other_views=[0.0])


@pytest.mark.parametrize('show_plotter', [
    True,
    False,
    ])
def test_background_plotter_export_files(qtbot, tmpdir, show_plotter, plotting):
    # setup filesystem
    output_dir = str(tmpdir.mkdir("tmpdir"))
    assert os.path.isdir(output_dir)

    plotter = BackgroundPlotter(
        show=show_plotter,
        off_screen=False,
        title='Testing Window'
    )
    assert_hasattr(plotter, "app_window", MainWindow)
    window = plotter.app_window  # MainWindow
    qtbot.addWidget(window)  # register the window

    # show the window
    if not show_plotter:
        assert not window.isVisible()
        with qtbot.wait_exposed(window):
            window.show()
    assert window.isVisible()

    plotter.add_mesh(pyvista.Sphere())
    assert_hasattr(plotter, "renderer", Renderer)
    renderer = plotter.renderer
    assert len(renderer._actors) == 1
    assert np.any(plotter.mesh.points)

    dlg = plotter._qt_screenshot(show=False)  # FileDialog
    qtbot.addWidget(dlg)  # register the dialog

    filename = str(os.path.join(output_dir, "tmp.png"))
    dlg.selectFile(filename)

    # show the dialog
    assert not dlg.isVisible()
    with qtbot.wait_exposed(dlg):
        dlg.show()
    assert dlg.isVisible()

    # synchronise signal and callback
    with qtbot.wait_signals([dlg.dlg_accepted], timeout=1000):
        dlg.accept()
    assert not dlg.isVisible()  # dialog is closed after accept()

    plotter.close()
    assert not window.isVisible()
    assert os.path.isfile(filename)


@pytest.mark.parametrize('show_plotter', [
    True,
    False,
    ])
def test_background_plotter_export_vtkjs(qtbot, tmpdir, show_plotter, plotting):
    # setup filesystem
    output_dir = str(tmpdir.mkdir("tmpdir"))
    assert os.path.isdir(output_dir)

    plotter = BackgroundPlotter(
        show=show_plotter,
        off_screen=False,
        title='Testing Window'
    )
    assert_hasattr(plotter, "app_window", MainWindow)
    window = plotter.app_window  # MainWindow
    qtbot.addWidget(window)  # register the window

    # show the window
    if not show_plotter:
        assert not window.isVisible()
        with qtbot.wait_exposed(window):
            window.show()
    assert window.isVisible()

    plotter.add_mesh(pyvista.Sphere())
    assert_hasattr(plotter, "renderer", Renderer)
    renderer = plotter.renderer
    assert len(renderer._actors) == 1
    assert np.any(plotter.mesh.points)

    dlg = plotter._qt_export_vtkjs(show=False)  # FileDialog
    qtbot.addWidget(dlg)  # register the dialog

    filename = str(os.path.join(output_dir, "tmp"))
    dlg.selectFile(filename)

    # show the dialog
    assert not dlg.isVisible()
    with qtbot.wait_exposed(dlg):
        dlg.show()
    assert dlg.isVisible()

    # synchronise signal and callback
    with qtbot.wait_signals([dlg.dlg_accepted], timeout=1000):
        dlg.accept()
    assert not dlg.isVisible()  # dialog is closed after accept()

    plotter.close()
    assert not window.isVisible()
    assert os.path.isfile(filename + '.vtkjs')


# vtkWeakReference and vtkFloatArray, only sometimes -- usually PySide2
# but also sometimes macOS
@pytest.mark.allow_bad_gc
def test_background_plotting_orbit(qtbot, plotting):
    plotter = BackgroundPlotter(off_screen=False, title='Testing Window')
    plotter.add_mesh(pyvista.Sphere())
    # perform the orbit:
    plotter.orbit_on_path(threaded=True, step=0.0)
    plotter.close()


def test_background_plotting_toolbar(qtbot, plotting):
    with pytest.raises(TypeError, match='toolbar'):
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

    with qtbot.wait_exposed(window):
        window.show()

    assert default_camera_tool_bar.isVisible()
    assert saved_cameras_tool_bar.isVisible()

    # triggering a view action
    plotter._view_action.trigger()

    plotter.close()


# TODO: _render_passes not GC'ed
@pytest.mark.allow_bad_gc_pyside
@pytest.mark.skipif(
    platform.system() == 'Windows', reason='Segfaults on Windows')
def test_background_plotting_menu_bar(qtbot, plotting):
    with pytest.raises(TypeError, match='menu_bar'):
        BackgroundPlotter(off_screen=False, menu_bar="foo")

    plotter = BackgroundPlotter(
        off_screen=False, menu_bar=False, update_app_icon=False)
    assert plotter.main_menu is None
    assert plotter._menu_close_action is None
    plotter.close()

    # menu_bar=True
    plotter = BackgroundPlotter(off_screen=False, update_app_icon=False)

    assert_hasattr(plotter, "app_window", MainWindow)
    assert_hasattr(plotter, "main_menu", QMenuBar)
    assert_hasattr(plotter, "_menu_close_action", QAction)
    assert_hasattr(plotter, "_edl_action", QAction)
    assert_hasattr(plotter, "_parallel_projection_action", QAction)

    window = plotter.app_window
    main_menu = plotter.main_menu
    assert not main_menu.isNativeMenuBar()

    with qtbot.wait_exposed(window):
        window.show()

    # EDL action
    if hasattr(plotter.renderer, '_render_passes'):
        obj, attr = plotter.renderer._render_passes, '_edl_pass'
    else:
        obj, attr = plotter.renderer, 'edl_pass'
    assert getattr(obj, attr, None) is None
    plotter._edl_action.trigger()
    assert getattr(obj, attr, None) is not None
    # and now test reset
    plotter._edl_action.trigger()

    # Parallel projection action
    assert not plotter.camera.GetParallelProjection()
    plotter._parallel_projection_action.trigger()
    assert plotter.camera.GetParallelProjection()
    # and now test reset
    plotter._parallel_projection_action.trigger()

    assert main_menu.isVisible()
    plotter.close()
    assert not main_menu.isVisible()
    assert plotter._last_update_time == -np.inf


def test_drop_event(tmpdir, qtbot):
    output_dir = str(tmpdir.mkdir("tmpdir"))
    filename = str(os.path.join(output_dir, "tmp.vtk"))
    mesh = pyvista.Cone()
    mesh.save(filename)
    assert os.path.isfile(filename)
    plotter = BackgroundPlotter(update_app_icon=False)
    with qtbot.wait_exposed(plotter.app_window, timeout=10000):
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


def test_drag_event(tmpdir):
    output_dir = str(tmpdir.mkdir("tmpdir"))
    filename = str(os.path.join(output_dir, "tmp.vtk"))
    mesh = pyvista.Cone()
    mesh.save(filename)
    assert os.path.isfile(filename)
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


def test_gesture_event(qtbot):
    plotter = BackgroundPlotter(update_app_icon=False)
    with qtbot.wait_exposed(plotter.app_window, timeout=10000):
        plotter.app_window.show()
    gestures = [QPinchGesture()]
    event = QGestureEvent(gestures)
    plotter.gesture_event(event)
    plotter.close()


def test_background_plotting_add_callback(qtbot, monkeypatch, plotting):
    class CallBack(object):
        def __init__(self, sphere):
            self.sphere = weakref.ref(sphere)

        def __call__(self):
            self.sphere().points[:] = self.sphere().points * 0.5

    update_count = [0]
    orig_update_app_icon = BackgroundPlotter.update_app_icon

    def update_app_icon(slf):
        update_count[0] = update_count[0] + 1
        return orig_update_app_icon(slf)

    monkeypatch.setattr(BackgroundPlotter, 'update_app_icon', update_app_icon)
    plotter = BackgroundPlotter(
        show=False,
        off_screen=False,
        title='Testing Window',
        update_app_icon=True,  # also does add_callback
    )
    assert_hasattr(plotter, "app_window", MainWindow)
    assert_hasattr(plotter, "_callback_timer", QTimer)
    assert_hasattr(plotter, "counters", list)
    assert plotter._last_update_time == -np.inf

    sphere = pyvista.Sphere()
    plotter.add_mesh(sphere)
    mycallback = CallBack(sphere)
    window = plotter.app_window  # MainWindow
    callback_timer = plotter._callback_timer  # QTimer
    assert callback_timer.isActive()

    # ensure that the window is showed
    assert not window.isVisible()
    with qtbot.wait_exposed(window):
        window.show()
    assert window.isVisible()
    assert update_count[0] in [0, 1]  # macOS sometimes updates (1)
    # don't check _last_update_time for non-inf-ness, won't be updated on Win
    plotter.update_app_icon()  # the timer doesn't call it right away, so do it
    assert update_count[0] in [1, 2]
    plotter.update_app_icon()  # should be a no-op
    assert update_count[0] in [2, 3]
    with pytest.raises(ValueError, match="ndarray with shape"):
        plotter.set_icon(0.)
    # Maybe someday manually setting "set_icon" should disable update_app_icon?
    # Strings also supported directly by QIcon
    plotter.set_icon(os.path.join(
        os.path.dirname(pyvistaqt.__file__), "data",
        "pyvista_logo_square.png"))
    callback_timer.stop()
    assert not callback_timer.isActive()

    # check that timers are set properly in add_callback()
    plotter.add_callback(mycallback, interval=200, count=3)
    callback_timer = plotter._callback_timer  # QTimer
    assert callback_timer.isActive()
    counter = plotter.counters[-1]  # Counter

    # ensure that self.callback_timer send a signal
    callback_blocker = qtbot.wait_signals([callback_timer.timeout], timeout=2000)
    callback_blocker.wait()
    # ensure that self.counters send a signal
    counter_blocker = qtbot.wait_signals([counter.signal_finished], timeout=2000)
    counter_blocker.wait()
    assert not callback_timer.isActive()  # counter stops the callback

    plotter.add_callback(mycallback, interval=200)
    callback_timer = plotter._callback_timer  # QTimer
    assert callback_timer.isActive()

    # ensure that self.callback_timer send a signal
    callback_blocker = qtbot.wait_signals([callback_timer.timeout], timeout=5000)
    callback_blocker.wait()

    plotter.close()
    assert not callback_timer.isActive()  # window stops the callback


def allow_bad_gc_old_pyvista(func):
    if Version(pyvista.__version__) < Version('0.37'):
        return pytest.mark.allow_bad_gc(func)
    else:
        return func


# TODO: Need to fix this allow_bad_gc:
# - the actors are not cleaned up in the non-empty scene case
# - the q_key_press leaves a lingering vtkUnsignedCharArray referred to by
#   a "managedbuffer" object
@allow_bad_gc_old_pyvista
@pytest.mark.allow_bad_gc_pyside
@pytest.mark.parametrize('close_event', [
    "plotter_close",
    "window_close",
    pytest.param("q_key_press", marks=pytest.mark.allow_bad_gc),
    "menu_exit",
    "del_finalizer",
    ])
@pytest.mark.parametrize('empty_scene', [
    True,
    False,
    ])
def test_background_plotting_close(qtbot, close_event, empty_scene, plotting):
    from pyvista.plotting.plotting import _ALL_PLOTTERS, close_all
    close_all()  # this is necessary to test _ALL_PLOTTERS
    assert len(_ALL_PLOTTERS) == 0

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
    with qtbot.wait_exposed(window, timeout=10000):
        window.show()
    with qtbot.wait_exposed(interactor, timeout=10000):
        interactor.show()

    # check that the widgets are showed properly
    assert window.isVisible()
    assert interactor.isVisible()
    assert main_menu.isVisible()
    assert render_timer.isActive()
    assert not plotter._closed

    with qtbot.wait_signals([window.signal_close], timeout=500):
        if close_event == "plotter_close":
            plotter.close()
        elif close_event == "window_close":
            window.close()
        elif close_event == "q_key_press":
            qtbot.keyClick(interactor, "q")
        elif close_event == "menu_exit":
            plotter._menu_close_action.trigger()
        elif close_event == "del_finalizer":
            plotter.__del__()

    # check that the widgets are closed
    assert not window.isVisible()
    assert not interactor.isVisible()
    assert not main_menu.isVisible()
    assert not render_timer.isActive()

    # check that BasePlotter.close() is called
    if Version(pyvista.__version__) < Version('0.27.0'):
        assert not hasattr(window.vtk_widget, "iren")
    assert plotter._closed

    assert len(_ALL_PLOTTERS) == WANT_AFTER


def test_multiplotter(qtbot, plotting):
    mp = MultiPlotter(
        nrows=1,
        ncols=2,
        window_size=(300, 300),
        show=False,
        title='Test',
        off_screen=False,
    )
    qtbot.addWidget(mp._window)
    mp[0, 0].add_mesh(pyvista.Cone())
    mp[0, 1].add_mesh(pyvista.Box())
    assert not mp._window.isVisible()
    with qtbot.wait_exposed(mp._window):
        mp.show()
    assert mp._window.isVisible()
    for p in mp._plotters:
        assert not p._closed
    with qtbot.wait_signals([mp._window.signal_close], timeout=1000):
        mp.close()
    for p in mp._plotters:
        assert p._closed

    # cover default show=True
    mp = MultiPlotter(off_screen=False, menu_bar=False, toolbar=False)
    qtbot.addWidget(mp._window)
    with qtbot.wait_exposed(mp._window):
        assert mp._window.isVisible()
    mp.close()


def _create_testing_scene(empty_scene, show=False, off_screen=False):
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
            border_color='grey',
            show=show,
            off_screen=off_screen,
            update_app_icon=False,
        )
        plotter.set_background('black', top='blue')
        plotter.subplot(0, 0)
        cone = pyvista.Cone(resolution=4)
        actor = plotter.add_mesh(cone)
        plotter.remove_actor(actor)
        plotter.add_text('Actor is removed')
        plotter.subplot(0, 1)
        plotter.add_mesh(pyvista.Box(), color='green', opacity=0.8)
        plotter.subplot(1, 0)
        cylinder = pyvista.Cylinder(resolution=6)
        plotter.add_mesh(cylinder, smooth_shading=True)
        plotter.show_bounds()
        plotter.subplot(1, 1)
        sphere = pyvista.Sphere(
            phi_resolution=6,
            theta_resolution=6
        )
        plotter.add_mesh(sphere)
        plotter.enable_cell_picking()
    return plotter


def assert_hasattr(variable, attribute_name, variable_type):
    __tracebackhide__ = True
    assert hasattr(variable, attribute_name)
    assert isinstance(getattr(variable, attribute_name), variable_type)


def test_sphinx_gallery_scraping(qtbot, monkeypatch, plotting, tmpdir):
    pytest.importorskip('sphinx_gallery')
    monkeypatch.setattr(pyvista, 'BUILDING_GALLERY', True)

    plotter = BackgroundPlotter(off_screen=False, editor=False, show=True)

    # Adapted from pyvista/tests/test_scraper.py
    scraper = Scraper()
    src_dir = str(tmpdir)
    out_dir = op.join(str(tmpdir), '_build', 'html')
    img_fname = op.join(src_dir, 'auto_examples', 'images', 'sg_img.png')
    gallery_conf = {"src_dir": src_dir, "builder_name": "html"}
    target_file = op.join(src_dir, 'auto_examples', 'sg.py')
    block = None
    block_vars = dict(
        image_path_iterator=(img for img in [img_fname]),
        example_globals=dict(a=1),
        target_file=target_file,
    )
    os.makedirs(op.dirname(img_fname))
    assert not os.path.isfile(img_fname)
    os.makedirs(out_dir)
    scraper(block, block_vars, gallery_conf)
    assert os.path.isfile(img_fname)
    plotter.close()
