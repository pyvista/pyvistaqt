"""
This module contains the QtInteractor and BackgroundPlotter.

Diagram
^^^^^^^

.. code-block:: none

    BackgroundPlotter
    +-- QtInteractor
        |-- QVTKRenderWindowInteractor
        |   +-- QWidget
        +-- BasePlotter

    MainWindow
    +-- QMainWindow

Implementation
^^^^^^^^^^^^^^

.. code-block:: none

    BackgroundPlotter.__init__(...)
    |-- self.app_window = MainWindow()
    |-- self.frame = QFrame(parent=self.app_window)
    +-- QtInteractor.__init__(parent=self.frame)
        |-- QVTKRenderWindowInteractor.__init__(parent=parent)
        |   +-- QWidget.__init__(parent, flags)
        |-- BasePlotter.__init__(...)
        +-- self.ren_win = self.GetRenderWindow()

Because ``QVTKRenderWindowInteractor`` calls ``QWidget.__init__``, this will
actually trigger ``BasePlotter.__init__`` to be called with no arguments.
This cannot be solved (at least) because using ``super()`` because
``QVTKRenderWindowInteractor.__init__`` does not use ``super()``, and also it
might not be fixable because Qt is doing something in ``QWidget`` which is
probably entirely separate from the Python ``super()`` process.
We fix this by internally by temporarily monkey-patching
``BasePlotter.__init__`` with a no-op ``__init__``.
"""
import contextlib
import logging
import os
import platform
import time
import warnings
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

import numpy as np  # type: ignore
import pyvista
import scooby  # type: ignore
import vtk
from pyvista.plotting.plotting import BasePlotter
from pyvista.plotting.theme import rcParams
from pyvista.utilities import conditional_decorator, threaded
from qtpy import QtCore
from qtpy.QtCore import QSize, QTimer, Signal
from qtpy.QtWidgets import (
    QAction,
    QApplication,
    QFrame,
    QGestureEvent,
    QMenuBar,
    QToolBar,
    QVBoxLayout,
)
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from .counter import Counter
from .dialog import FileDialog, ScaleAxesDialog
from .editor import Editor
from .window import MainWindow

if scooby.in_ipython():  # pragma: no cover
    # pylint: disable=unused-import
    from IPython.external.qt_for_kernel import QtGui
else:
    from qtpy import QtGui  # pylint: disable=ungrouped-imports

LOG = logging.getLogger("pyvistaqt")
LOG.setLevel(logging.CRITICAL)
LOG.addHandler(logging.StreamHandler())


# for display bugs due to older intel integrated GPUs, setting
# vtkmodules.qt.QVTKRWIBase = 'QGLWidget' could help. However, its use
# is discouraged and does not work well on VTK9+, so let's not bother
# changing it from the default 'QWidget'.
# See https://github.com/pyvista/pyvista/pull/693

# LOG is unused at the moment
# LOG = logging.getLogger(__name__)
# LOG.setLevel('DEBUG')

SAVE_CAM_BUTTON_TEXT = "Save Camera"
CLEAR_CAMS_BUTTON_TEXT = "Clear Cameras"


def resample_image(arr: np.ndarray, max_size: int = 400) -> np.ndarray:
    """Resample a square image to an image of max_size."""
    dim = np.max(arr.shape[0:2])
    max_size = min(max_size, dim)
    x_size, y_size, _ = arr.shape
    s_x = int(np.ceil(x_size / max_size))
    s_y = int(np.ceil(y_size / max_size))
    img = np.zeros((max_size, max_size, arr.shape[2]), dtype=arr.dtype)
    arr = arr[0:-1:s_x, 0:-1:s_y, :]
    x_l = (max_size - arr.shape[0]) // 2
    y_l = (max_size - arr.shape[1]) // 2
    img[x_l : arr.shape[0] + x_l, y_l : arr.shape[1] + y_l, :] = arr
    return img


def pad_image(arr: np.ndarray, max_size: int = 400) -> np.ndarray:
    """Pad an image to a square then resamples to max_size."""
    dim = np.max(arr.shape)
    img = np.zeros((dim, dim, arr.shape[2]), dtype=arr.dtype)
    x_l = (dim - arr.shape[0]) // 2
    y_l = (dim - arr.shape[1]) // 2
    img[x_l : arr.shape[0] + x_l, y_l : arr.shape[1] + y_l, :] = arr
    return resample_image(img, max_size=max_size)


@contextlib.contextmanager
def _no_base_plotter_init() -> Generator[None, None, None]:
    init = BasePlotter.__init__
    BasePlotter.__init__ = lambda x: None
    try:
        yield
    finally:
        BasePlotter.__init__ = init


class QtInteractor(QVTKRenderWindowInteractor, BasePlotter):
    """Extend QVTKRenderWindowInteractor class.

    This adds the methods available to pyvista.Plotter.

    Parameters
    ----------
    parent :
        Qt parent.

    title :
        Title of plotting window.

    multi_samples :
        The number of multi-samples used to mitigate aliasing. 4 is a
        good default but 8 will have better results with a potential
        impact on performance.

    line_smoothing :
        If True, enable line smothing

    point_smoothing :
        If True, enable point smothing

    polygon_smoothing :
        If True, enable polygon smothing

    auto_update :
        Automatic update rate in seconds.  Useful for automatically
        updating the render window when actors are change without
        being automatically ``Modified``.
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-statements

    # Signals must be class attributes
    render_signal = Signal()
    key_press_event_signal = Signal(vtk.vtkGenericRenderWindowInteractor, str)

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        parent: MainWindow = None,
        title: str = None,
        off_screen: bool = None,
        multi_samples: int = None,
        line_smoothing: bool = False,
        point_smoothing: bool = False,
        polygon_smoothing: bool = False,
        auto_update: Union[float, bool] = 5.0,
        **kwargs: Any
    ) -> None:
        # pylint: disable=too-many-branches
        """Initialize Qt interactor."""
        LOG.debug("QtInteractor init start")

        self.url: QtCore.QUrl = None
        self.default_camera_tool_bar = None
        self.saved_camera_positions: Optional[List[BasePlotter.camera_position]] = None
        self.saved_cameras_tool_bar: QToolBar = None
        self.main_menu: QMenuBar = None
        self._menu_close_action = None
        self._edl_action = None
        self._parallel_projection_action = None
        self._view_action = None

        # Cannot use super() here because
        # QVTKRenderWindowInteractor silently swallows all kwargs
        # because they use **kwargs in their constructor...
        qvtk_kwargs = dict(parent=parent)
        for key in ("stereo", "iren", "rw", "wflags"):
            if key in kwargs:
                qvtk_kwargs[key] = kwargs.pop(key)
        with _no_base_plotter_init():
            QVTKRenderWindowInteractor.__init__(self, **qvtk_kwargs)
        BasePlotter.__init__(self, **kwargs)
        # backward compat for when we had this as a separate class
        self.interactor = self

        if multi_samples is None:
            multi_samples = rcParams["multi_samples"]

        self.setAcceptDrops(True)

        # Create and start the interactive renderer
        self.ren_win = self.GetRenderWindow()
        self.ren_win.SetMultiSamples(multi_samples)
        if line_smoothing:
            self.ren_win.LineSmoothingOn()
        if point_smoothing:
            self.ren_win.PointSmoothingOn()
        if polygon_smoothing:
            self.ren_win.PolygonSmoothingOn()

        for renderer in self.renderers:
            self.ren_win.AddRenderer(renderer)

        self.render_signal.connect(self._render)
        self.key_press_event_signal.connect(super(QtInteractor, self).key_press_event)

        self.background_color = rcParams["background"]
        if self.title:
            self.setWindowTitle(title)

        if off_screen is None:
            off_screen = pyvista.OFF_SCREEN

        if off_screen:
            self.ren_win.SetOffScreenRendering(1)
            self.iren = None
        else:
            self.iren = self.ren_win.GetInteractor()
            self.iren.RemoveObservers("MouseMoveEvent")  # slows window update?

            # Enter trackball camera mode
            istyle = vtk.vtkInteractorStyleTrackballCamera()
            self.SetInteractorStyle(istyle)

            self.iren.Initialize()

            self._observers: Dict[
                None, None
            ] = {}  # Map of events to observers of self.iren
            self._add_observer("KeyPressEvent", self.key_press_event)

        # Make the render timer but only activate if using auto update
        self.render_timer = QTimer(parent=parent)
        if float(auto_update) > 0.0:  # Can be False as well
            # Spawn a thread that updates the render window.
            # Sometimes directly modifiying object data doesn't trigger
            # Modified() and upstream objects won't be updated.  This
            # ensures the render window stays updated without consuming too
            # many resources.
            twait = (auto_update ** -1) * 1000.0
            self.render_timer.timeout.connect(self.render)
            self.render_timer.start(twait)

        if rcParams["depth_peeling"]["enabled"]:
            if self.enable_depth_peeling():
                for renderer in self.renderers:
                    renderer.enable_depth_peeling()

        self._first_time = False  # Crucial!
        self.view_isometric()
        LOG.debug("QtInteractor init stop")

    def gesture_event(self, event: QGestureEvent) -> bool:
        """Handle gesture events."""
        pinch = event.gesture(QtCore.Qt.PinchGesture)
        if pinch:
            self.camera.Zoom(pinch.scaleFactor())
            event.accept()
        return True

    def key_press_event(self, obj: Any, event: Any) -> None:
        """Call `key_press_event` using a signal."""
        self.key_press_event_signal.emit(obj, event)

    @wraps(BasePlotter.render)
    def _render(self, *args: Any, **kwargs: Any) -> BasePlotter.render:
        """Wrap ``BasePlotter.render``."""
        return BasePlotter.render(self, *args, **kwargs)

    @conditional_decorator(threaded, platform.system() == "Darwin")
    def render(self) -> None:
        """Override the ``render`` method to handle threading issues."""
        return self.render_signal.emit()

    @wraps(BasePlotter.enable)
    def enable(self) -> None:
        """Wrap ``BasePlotter.enable``."""
        self.setEnabled(True)
        return BasePlotter.enable(self)

    @wraps(BasePlotter.disable)
    def disable(self) -> None:
        """Wrap ``BasePlotter.disable``."""
        self.setDisabled(True)
        return BasePlotter.disable(self)

    # pylint: disable=invalid-name,no-self-use
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        """Event is called when something is dropped onto the vtk window.

        Only triggers event when event contains file paths that
        exist.  User can drop anything in this window and we only want
        to allow files.
        """
        # pragma: no cover
        try:
            for url in event.mimeData().urls():
                if os.path.isfile(url.path()):
                    # only call accept on files
                    event.accept()
        except IOError as exception:  # pragma: no cover
            warnings.warn("Exception when dropping files: %s" % str(exception))

    # pylint: disable=invalid-name,useless-return
    def dropEvent(self, event: QtCore.QEvent) -> None:
        """Event is called after dragEnterEvent."""
        for url in event.mimeData().urls():  # pragma: no cover
            self.url = url
            filename = self.url.path()
            if os.path.isfile(filename):
                try:
                    self.add_mesh(pyvista.read(filename))
                except IOError as exception:
                    print(str(exception))
        return None

    def add_toolbars(self) -> None:  # pylint: disable=useless-return
        """Add the toolbars."""

        def _add_action(tool_bar: QToolBar, key: str, method: Any) -> QAction:
            action = QAction(key, self.app_window)
            action.triggered.connect(method)
            tool_bar.addAction(action)
            return action

        # Camera toolbar
        self.default_camera_tool_bar = self.app_window.addToolBar("Camera Position")

        def _view_vector(*args: Any) -> None:
            return self.view_vector(*args)

        cvec_setters = {
            # Viewing vector then view up vector
            "Top (-Z)": lambda: _view_vector((0, 0, 1), (0, 1, 0)),
            "Bottom (+Z)": lambda: _view_vector((0, 0, -1), (0, 1, 0)),
            "Front (-Y)": lambda: _view_vector((0, 1, 0), (0, 0, 1)),
            "Back (+Y)": lambda: _view_vector((0, -1, 0), (0, 0, 1)),
            "Left (-X)": lambda: _view_vector((1, 0, 0), (0, 0, 1)),
            "Right (+X)": lambda: _view_vector((-1, 0, 0), (0, 0, 1)),
            "Isometric": lambda: _view_vector((1, 1, 1), (0, 0, 1)),
        }
        for key, method in cvec_setters.items():
            self._view_action = _add_action(self.default_camera_tool_bar, key, method)
        # pylint: disable=unnecessary-lambda
        _add_action(self.default_camera_tool_bar, "Reset", lambda: self.reset_camera())

        # Saved camera locations toolbar
        self.saved_camera_positions = []
        self.saved_cameras_tool_bar = self.app_window.addToolBar(
            "Saved Camera Positions"
        )

        _add_action(
            self.saved_cameras_tool_bar, SAVE_CAM_BUTTON_TEXT, self.save_camera_position
        )
        _add_action(
            self.saved_cameras_tool_bar,
            CLEAR_CAMS_BUTTON_TEXT,
            self.clear_camera_positions,
        )

        return None

    def add_menu_bar(self) -> None:
        """Add the main menu bar."""
        self.main_menu = _create_menu_bar(parent=self.app_window)
        self.app_window.signal_close.connect(self.main_menu.clear)

        file_menu = self.main_menu.addMenu("File")
        file_menu.addAction("Take Screenshot", self._qt_screenshot)
        file_menu.addAction("Export as VTKjs", self._qt_export_vtkjs)
        file_menu.addSeparator()
        # member variable for testing only
        self._menu_close_action = file_menu.addAction("Exit", self.app_window.close)

        view_menu = self.main_menu.addMenu("View")
        self._edl_action = view_menu.addAction(
            "Toggle Eye Dome Lighting", self._toggle_edl
        )
        view_menu.addAction("Scale Axes", self.scale_axes_dialog)
        view_menu.addAction("Clear All", self.clear)

        tool_menu = self.main_menu.addMenu("Tools")
        tool_menu.addAction("Enable Cell Picking (through)", self.enable_cell_picking)
        tool_menu.addAction(
            "Enable Cell Picking (visible)",
            lambda: self.enable_cell_picking(through=False),
        )

        cam_menu = view_menu.addMenu("Camera")
        self._parallel_projection_action = cam_menu.addAction(
            "Toggle Parallel Projection", self._toggle_parallel_projection
        )

        view_menu.addSeparator()
        # Orientation marker
        orien_menu = view_menu.addMenu("Orientation Marker")
        orien_menu.addAction("Show All", self.show_axes_all)
        orien_menu.addAction("Hide All", self.hide_axes_all)
        # Bounds axes
        axes_menu = view_menu.addMenu("Bounds Axes")
        axes_menu.addAction("Add Bounds Axes (front)", self.show_bounds)
        axes_menu.addAction("Add Bounds Grid (back)", self.show_grid)
        axes_menu.addAction("Add Bounding Box", self.add_bounding_box)
        axes_menu.addSeparator()
        axes_menu.addAction("Remove Bounding Box", self.remove_bounding_box)
        axes_menu.addAction("Remove Bounds", self.remove_bounds_axes)

        # A final separator to separate OS options
        view_menu.addSeparator()

    def save_camera_position(self) -> None:
        """Save camera position to saved camera menu for recall."""
        if self.saved_camera_positions is not None:
            # pylint: disable=attribute-defined-outside-init
            self.camera_position: Any
            self.saved_camera_positions.append(self.camera_position)
            ncam = len(self.saved_camera_positions)
        if self.camera_position is not None:
            camera_position: Any = self.camera_position[:]  # py2.7 copy compatibility

        if hasattr(self, "saved_cameras_tool_bar"):

            def load_camera_position() -> None:
                # pylint: disable=attribute-defined-outside-init
                self.camera_position = camera_position

            self.saved_cameras_tool_bar.addAction(
                "Cam %2d" % ncam, load_camera_position
            )
            if ncam < 10:
                self.add_key_event(str(ncam), load_camera_position)

    def clear_camera_positions(self) -> None:
        """Clear all camera positions."""
        if hasattr(self, "saved_cameras_tool_bar"):
            for action in self.saved_cameras_tool_bar.actions():
                if action.text() not in [SAVE_CAM_BUTTON_TEXT, CLEAR_CAMS_BUTTON_TEXT]:
                    self.saved_cameras_tool_bar.removeAction(action)
        self.saved_camera_positions = []

    def close(self) -> None:
        """Quit application."""
        if self._closed:
            return
        if hasattr(self, "render_timer"):
            self.render_timer.stop()
        BasePlotter.close(self)
        QVTKRenderWindowInteractor.close(self)


class BackgroundPlotter(QtInteractor):
    """Qt interactive plotter.

    Background plotter for pyvista that allows you to maintain an
    interactive plotting window without blocking the main python
    thread.

    Parameters
    ----------
    show :
        Show the plotting window.  If ``False``, show this window by
        running ``show()``

    app : optional
        Creates a `QApplication` if left as `None`.

    window_size :
        Window size in pixels.  Defaults to ``[1024, 768]``

    off_screen :
        Renders off screen when True.  Useful for automated
        screenshots or debug testing.

    allow_quit_keypress :
        Allow user to exit by pressing ``"q"``.

    toolbar : bool
        If True, display the default camera toolbar. Defaults to True.

    menu_bar : bool
        If True, display the default main menu. Defaults to True.

    editor: bool
        If True, display the VTK object editor. Defaults to True.

    update_app_icon :
        If True, update_app_icon will be called automatically to update the
        Qt app icon based on the current rendering output.

    title : str, optional
        Title of plotting window.

    multi_samples : int, optional
        The number of multi-samples used to mitigate aliasing. 4 is a
        good default but 8 will have better results with a potential
        impact on performance.

    line_smoothing : bool, optional
        If True, enable line smothing

    point_smoothing : bool, optional
        If True, enable point smothing

    polygon_smoothing : bool, optional
        If True, enable polygon smothing

    auto_update : float, bool, optional
        Automatic update rate in seconds.  Useful for automatically
        updating the render window when actors are change without
        being automatically ``Modified``.  If set to ``True``, update
        rate will be 1 second.

    Examples
    --------
    >>> import pyvista as pv
    >>> from pyvistaqt import BackgroundPlotter
    >>> plotter = BackgroundPlotter()
    >>> _ = plotter.add_mesh(pv.Sphere())
    """

    # pylint: disable=too-many-ancestors
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-statements

    ICON_TIME_STEP = 5.0

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    def __init__(
        self,
        show: bool = True,
        app: QApplication = None,
        window_size: Optional[Tuple[int, int]] = None,
        off_screen: bool = None,
        allow_quit_keypress: bool = True,
        toolbar: bool = True,
        menu_bar: bool = True,
        editor: bool = True,
        update_app_icon: bool = False,
        **kwargs: Any
    ) -> None:
        # pylint: disable=too-many-branches
        """Initialize the qt plotter."""
        # avoid recursion of the close() function by setting
        # self._closed=True until the BasePlotter.__init__
        # is called
        self._closed = True
        LOG.debug("BackgroundPlotter init start")
        if not isinstance(menu_bar, bool):
            raise TypeError(
                "Expected type for ``menu_bar`` is bool"
                " but {} was given.".format(type(menu_bar))
            )
        if not isinstance(toolbar, bool):
            raise TypeError(
                "Expected type for ``toolbar`` is bool"
                " but {} was given.".format(type(toolbar))
            )

        self.active = True
        self.counters: List[Counter] = []
        self.allow_quit_keypress = allow_quit_keypress

        if window_size is None:
            window_size = rcParams["window_size"]

        # Remove notebook argument in case user passed it
        kwargs.pop("notebook", None)

        # ipython magic
        if scooby.in_ipython():  # pragma: no cover
            # pylint: disable=import-outside-toplevel
            from IPython import get_ipython

            ipython = get_ipython()
            ipython.magic("gui qt")

            # pylint: disable=redefined-outer-name
            # pylint: disable=import-outside-toplevel
            from IPython.external.qt_for_kernel import QtGui

            QtGui.QApplication.instance()
        else:
            ipython = None

        # run within python
        if app is None:
            app = QApplication.instance()
            if not app:  # pragma: no cover
                app = QApplication(["PyVista"])

        self.app = app
        self.app_window = MainWindow()
        self.app_window.setWindowTitle(kwargs.get("title", rcParams["title"]))

        self.frame = QFrame(parent=self.app_window)
        self.frame.setFrameStyle(QFrame.NoFrame)
        self.app_window.setCentralWidget(self.frame)
        vlayout = QVBoxLayout()
        self.frame.setLayout(vlayout)
        super(BackgroundPlotter, self).__init__(
            parent=self.frame, off_screen=off_screen, **kwargs
        )
        assert not self._closed
        vlayout.addWidget(self)
        self.app_window.grabGesture(QtCore.Qt.PinchGesture)
        self.app_window.signal_gesture.connect(self.gesture_event)
        self.app_window.signal_close.connect(self._close)

        self.main_menu = None
        self._menu_close_action = None
        if menu_bar:
            self.add_menu_bar()

        self.editor = None
        if editor and menu_bar:
            self.add_editor()

        # member variable for testing only
        self._view_action = None

        self.default_camera_tool_bar = None
        self.saved_camera_positions = None
        self.saved_cameras_tool_bar = None
        if toolbar:
            self.add_toolbars()

        if off_screen is None:
            off_screen = pyvista.OFF_SCREEN

        if show and not off_screen:  # pragma: no cover
            self.app_window.show()
            self.show()

        self.window_size = window_size
        self._last_update_time = -np.inf
        self._last_window_size = self.window_size
        self._last_camera_pos = self.camera_position

        if update_app_icon:
            self.add_callback(self.update_app_icon)
        else:
            self.set_icon(
                os.path.join(
                    os.path.dirname(__file__), "data", "pyvista_logo_square.png"
                )
            )

        # Keypress events
        self.add_key_event("S", self._qt_screenshot)  # shift + s
        LOG.debug("BackgroundPlotter init stop")

    def reset_key_events(self) -> None:
        """Reset all of the key press events to their defaults.

        Handles closing configuration for q-key.
        """
        super(BackgroundPlotter, self).reset_key_events()
        if self.allow_quit_keypress:
            # pylint: disable=unnecessary-lambda
            self.add_key_event("q", lambda: self.close())

    def scale_axes_dialog(self, show: bool = True) -> ScaleAxesDialog:
        """Open scale axes dialog."""
        return ScaleAxesDialog(self.app_window, self, show=show)

    def close(self) -> None:
        """Close the plotter.

        This function closes the window which in turn will
        close the plotter through `signal_close`.

        """
        if not self._closed:
            self.app_window.close()

    def _close(self) -> None:
        super().close()

    def update_app_icon(self) -> None:
        """Update the app icon if the user is not trying to resize the window."""
        if os.name == "nt" or not hasattr(
            self, "_last_window_size"
        ):  # pragma: no cover
            # DO NOT EVEN ATTEMPT TO UPDATE ICON ON WINDOWS
            return
        cur_time = time.time()
        if self._last_window_size != self.window_size:  # pragma: no cover
            # Window size hasn't remained constant since last render.
            # This means the user is resizing it so ignore update.
            pass
        elif (
            cur_time - self._last_update_time > BackgroundPlotter.ICON_TIME_STEP
        ) and self._last_camera_pos != self.camera_position:
            # its been a while since last update OR
            # the camera position has changed and its been at least one second

            # Update app icon as preview of the window
            self.set_icon(pad_image(self.image))

            # Update trackers
            self._last_update_time = cur_time
            self._last_camera_pos = self.camera_position
        # Update trackers
        self._last_window_size = self.window_size

    def set_icon(self, img: np.ndarray) -> None:
        """Set the icon image.

        Parameters
        ----------
        img : shape (w, h, c) | str
            The image. Should be uint8 and square (w == h).
            Can have 3 or 4 color/alpha channels (``c``).
            Can also be a string path that QIcon can load.

        Notes
        -----
        Currently string paths can silently fail, so make sure your path
        is something that produces a valid ``QIcon(img)``.
        """
        if not (
            isinstance(img, np.ndarray)
            and img.ndim == 3
            and img.shape[0] == img.shape[1]
            and img.dtype == np.uint8
            and img.shape[-1] in (3, 4)
        ) and not isinstance(img, str):
            raise ValueError(
                "img must be 3D uint8 ndarray with shape[1] == shape[2] and "
                "shape[2] == 3 or 4, or str"
            )
        if isinstance(img, np.ndarray):
            fmt_str = "Format_RGB"
            fmt_str += ("A8" if img.shape[2] == 4 else "") + "888"
            fmt = getattr(QtGui.QImage, fmt_str)
            img = QtGui.QPixmap.fromImage(
                QtGui.QImage(img.copy(), img.shape[1], img.shape[0], fmt)
            )
        # Currently no way to check if str/path is actually correct (want to
        # allow resource paths and the like so os.path.isfile is no good)
        # and icon.isNull() returns False even if the path is bogus.
        self.app.setWindowIcon(QtGui.QIcon(img))

    def _qt_screenshot(self, show: bool = True) -> FileDialog:
        return FileDialog(
            self.app_window,
            filefilter=["Image File (*.png)", "JPEG (*.jpeg)"],
            show=show,
            directory=bool(os.getcwd()),
            callback=self.screenshot,
        )

    def _qt_export_vtkjs(self, show: bool = True) -> FileDialog:
        """Spawn an save file dialog to export a vtkjs file."""
        return FileDialog(
            self.app_window,
            filefilter=["VTK JS File(*.vtkjs)"],
            show=show,
            directory=bool(os.getcwd()),
            callback=self.export_vtkjs,
        )

    def _toggle_edl(self) -> None:
        if hasattr(self.renderer, "edl_pass"):
            return self.renderer.disable_eye_dome_lighting()
        return self.renderer.enable_eye_dome_lighting()

    def _toggle_parallel_projection(self) -> None:
        if self.camera.GetParallelProjection():
            return self.disable_parallel_projection()
        return self.enable_parallel_projection()

    @property
    def window_size(self) -> Tuple[int, int]:
        """Return render window size."""
        the_size = self.app_window.baseSize()
        return the_size.width(), the_size.height()

    @window_size.setter
    def window_size(self, window_size: QSize) -> None:
        """Set the render window size."""
        self.app_window.setBaseSize(*window_size)
        self.app_window.resize(*window_size)
        # NOTE: setting BasePlotter is unnecessary and Segfaults CI
        # BasePlotter.window_size.fset(self, window_size)

    def __del__(self) -> None:  # pragma: no cover
        """Delete the qt plotter."""
        if not self._closed:
            self.app_window.close()

    def add_callback(
        self, func: Callable, interval: int = 1000, count: Optional[int] = None
    ) -> None:
        """Add a function that can update the scene in the background.

        Parameters
        ----------
        func :
            Function to be called with no arguments.
        interval :
            Time interval between calls to `func` in milliseconds.
        count :
            Number of times `func` will be called. If None,
            `func` will be called until the main window is closed.

        """
        self._callback_timer = QTimer(parent=self.app_window)
        self._callback_timer.timeout.connect(func)
        self._callback_timer.start(interval)
        self.app_window.signal_close.connect(self._callback_timer.stop)
        if count is not None:
            counter = Counter(count)
            counter.signal_finished.connect(self._callback_timer.stop)
            self._callback_timer.timeout.connect(counter.decrease)
            self.counters.append(counter)

    def add_editor(self) -> None:
        """Add the editor."""
        self.editor = Editor(parent=self.app_window, renderers=self.renderers)
        self._editor_action = self.main_menu.addAction("Editor", self.editor.toggle)
        self.app_window.signal_close.connect(self.editor.close)


def _create_menu_bar(parent: Any) -> QMenuBar:
    """Create a menu bar.

    The menu bar is expected to behave consistently
    for every operating system since `setNativeMenuBar(False)`
    is called by default and therefore lifetime and ownership can
    be tested.
    """
    menu_bar = QMenuBar(parent=parent)
    menu_bar.setNativeMenuBar(False)
    if parent is not None:
        parent.setMenuBar(menu_bar)
    return menu_bar
