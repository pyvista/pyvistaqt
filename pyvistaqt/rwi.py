"""
FBO-based QVTKRenderWindowInteractor (rendering core).

A Python translation of VTK's C++ ``QVTKOpenGLNativeWidget`` +
``QVTKRenderWindowAdapter`` (GUISupport/Qt, BSD-3-Clause): a ``QOpenGLWidget``
that drives a ``vtkGenericOpenGLRenderWindow`` rendering into Qt-managed
framebuffer objects. No native window handle is ever passed to VTK, so the
widget is display-server agnostic and works natively on Wayland (gh-445).

Key design points mirrored from the C++ adapter:

- VTK never owns the GL context. ``WindowMakeCurrentEvent`` is serviced with
  ``QOpenGLContext.makeCurrent(surface)`` -- deliberately *not*
  ``QOpenGLWidget.makeCurrent()``, which also rebinds the widget's backing
  framebuffer and would corrupt VTK's framebuffer bindings mid-render.
- With ``SwapBuffers`` on, ``vtkOpenGLRenderWindow::Frame()`` resolves the
  frame into VTK's *display* framebuffer; ``FrameBlitModeToNoBlit`` only stops
  VTK from blitting it anywhere further. ``paintGL`` then blits the display
  framebuffer into the widget's default FBO (``BlitDisplayFramebuffer``), and
  clears the target's alpha to 1 so the compositor does not blend the window
  with whatever is behind it (Mesa/macOS; see paraview/paraview#17159).
- ``vtkRenderWindow.Render()`` may be called from anywhere (pyvistaqt's render
  timer and ``BasePlotter`` do this): the render happens immediately into
  VTK's FBOs and ``WindowFrameEvent`` schedules a repaint that blits the
  result into the widget's framebuffer.
- ``vtkGenericOpenGLRenderWindow::Render()`` resets VTK's OpenGL state cache
  and silently skips rendering unless ``IsCurrent()`` is true, so the
  make-current/is-current observers are correctness-critical.

Hard-won invariants (each was found by debugging a real failure; violating any
of them produces symptoms that are far removed from the cause):

1. Service ``WindowMakeCurrentEvent`` with ``QOpenGLContext.makeCurrent`` on
   the surface captured in ``initializeGL`` -- never with
   ``QOpenGLWidget.makeCurrent()``. The widget variant also binds the widget's
   backing framebuffer *every call*, which corrupts VTK's framebuffer-binding
   bookkeeping mid-render. Because ``vtkGenericOpenGLRenderWindow::Render()``
   silently skips rendering (TRACE log only) when ``IsCurrent()`` is false,
   the corruption manifests as stale/garbled frames and mutually inconsistent
   pixel readbacks rather than an error.
2. The GL surface format must be installed process-wide with
   ``QSurfaceFormat.setDefaultFormat()`` *before the top-level window is
   created* -- a per-widget ``setFormat()`` makes the widget's context
   incompatible with the top-level window's share context on Wayland and the
   widget composites black (reproducible with a plain magenta-clearing
   ``QOpenGLWidget``; the format *content* is irrelevant). Setting the default
   in ``__init__`` also covers applications that created the ``QApplication``
   themselves. The default format additionally requests desktop OpenGL
   explicitly, since Wayland/EGL may otherwise return a GLES context whose
   GLSL rejects VTK's ``#version 150`` shaders.
3. ``paintGL`` must *always* render, unlike C++
   ``QVTKOpenGLNativeWidget::paintGL`` which skips the VTK render for paints
   scheduled by a finished render's ``WindowFrameEvent``. pyvista mutates the
   scene (cameras, actors) without asking the widget to repaint, so a skipped
   render blits a stale frame (caught by ``test_background_plotting_plots``:
   the last-active subplot showed a pre-``camera.zoom`` frame). This matches
   the behavior of the previously vendored ``QVTKRenderWindowInteractor``.
4. Never call ``QWidget.screen()``: the Python binding can end up owning the
   returned application-global ``QScreen``, and a later garbage collection
   then deletes it, crashing much later inside an unrelated
   ``QMainWindow()`` construction (``QScreen::virtualSiblings`` use after
   free). VTK only needs the screen size for fullscreen render windows, which
   do not apply to an embedded widget, so ``SetScreenSize`` is simply not
   called.
5. GL resource teardown must happen with our context current. The
   ``aboutToBeDestroyed`` slot makes the context current itself (Qt's
   canonical cleanup pattern) before ``Finalize``; ``closeEvent`` must *not*
   call ``QOpenGLWidget.makeCurrent()`` because it can run while the parent
   window is being destroyed (via the ``destroyed`` -> ``close`` connection),
   and ``Finalize`` already drives ``MakeCurrent`` through the observer.
   Freeing GL objects against the wrong context is driver heap corruption
   that, like (4), crashes at a distance.
"""

from collections.abc import Callable
import contextlib
import ctypes
from typing import Any
from typing import ClassVar
from typing import cast

from qtpy.QtCore import QEvent
from qtpy.QtCore import QRect
from qtpy.QtCore import QSize
from qtpy.QtCore import Qt
from qtpy.QtCore import QTimer
from qtpy.QtGui import QOpenGLContext
from qtpy.QtGui import QSurfaceFormat
from qtpy.QtOpenGLWidgets import QOpenGLWidget
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QSizePolicy
from vtkmodules.vtkRenderingOpenGL2 import vtkGenericOpenGLRenderWindow
from vtkmodules.vtkRenderingUI import vtkGenericRenderWindowInteractor

# OpenGL enums (PyOpenGL is not a dependency).
GL_READ_FRAMEBUFFER = 0x8CA8
GL_DRAW_FRAMEBUFFER = 0x8CA9
GL_COLOR_ATTACHMENT0 = 0x8CE0
GL_SCISSOR_TEST = 0x0C11
GL_COLOR_BUFFER_BIT = 0x00004000
GL_LINEAR = 0x2601
GL_DEPTH_TEST = 0x0B71
GL_LEQUAL = 0x0203


def _default_format() -> QSurfaceFormat:
    """Desktop-GL 3.2 core format (QVTKRenderWindowAdapter::defaultFormat)."""
    fmt = QSurfaceFormat()
    # Explicitly request desktop OpenGL: on Wayland/EGL Qt may otherwise hand
    # back a GLES context, whose GLSL rejects VTK's ``#version 150`` shaders.
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setVersion(3, 2)
    fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
    fmt.setRedBufferSize(8)
    fmt.setGreenBufferSize(8)
    fmt.setBlueBufferSize(8)
    fmt.setDepthBufferSize(8)
    fmt.setAlphaBufferSize(8)
    fmt.setStencilBufferSize(0)
    fmt.setSamples(0)  # MSAA happens in VTK's FBOs, not the Qt context
    return fmt


class _GLAPI:
    """
    Raw OpenGL entry points resolved through ``QOpenGLContext.getProcAddress``.

    PyQt6 wraps neither ``QOpenGLContext.functions()``/``extraFunctions()`` nor
    the ``QOpenGLFunctions`` classes, so the few raw GL calls the blit needs are
    resolved through the context (whose loader handles wgl/glX/egl per
    platform) and called via ctypes. The context must be current both when
    resolving and when calling.
    """

    # filled in by __init__ from _SIGNATURES via setattr
    glBindFramebuffer: Callable[..., Any]
    glDrawBuffers: Callable[..., Any]
    glIsEnabled: Callable[..., Any]
    glEnable: Callable[..., Any]
    glDisable: Callable[..., Any]
    glColorMask: Callable[..., Any]
    glClearColor: Callable[..., Any]
    glViewport: Callable[..., Any]
    glClear: Callable[..., Any]

    _SIGNATURES: ClassVar[dict[str, tuple]] = {
        "glBindFramebuffer": (None, ctypes.c_uint, ctypes.c_uint),
        "glDrawBuffers": (None, ctypes.c_int, ctypes.POINTER(ctypes.c_uint)),
        "glIsEnabled": (ctypes.c_ubyte, ctypes.c_uint),
        "glEnable": (None, ctypes.c_uint),
        "glDisable": (None, ctypes.c_uint),
        "glColorMask": (None, ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ubyte),
        "glClearColor": (None, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float),
        "glViewport": (None, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int),
        "glClear": (None, ctypes.c_uint),
    }

    def __init__(self, ctx):
        for name, (res, *args) in self._SIGNATURES.items():
            ptr = ctx.getProcAddress(name.encode())
            addr = int(ptr) if ptr is not None else 0
            if addr == 0:  # all of these are core in any GL >= 3.0 context
                msg = f"could not resolve OpenGL function {name!r}"
                raise RuntimeError(msg)
            setattr(self, name, ctypes.CFUNCTYPE(res, *args)(addr))

    def draw_buffer_attachment0(self):
        """glDrawBuffers(1, [GL_COLOR_ATTACHMENT0])."""
        bufs = (ctypes.c_uint * 1)(GL_COLOR_ATTACHMENT0)
        self.glDrawBuffers(1, bufs)


def _get_event_pos(ev):
    try:  # Qt6+
        return ev.position().x(), ev.position().y()
    except AttributeError:  # Qt5
        return ev.x(), ev.y()


class QVTKRenderWindowInteractor(QOpenGLWidget):
    """A ``QOpenGLWidget`` housing a ``vtkGenericOpenGLRenderWindow``."""

    # Map between VTK and Qt cursors.
    _CURSOR_MAP: ClassVar[dict[int, Qt.CursorShape]] = {
        0: Qt.CursorShape.ArrowCursor,  # VTK_CURSOR_DEFAULT
        1: Qt.CursorShape.ArrowCursor,  # VTK_CURSOR_ARROW
        2: Qt.CursorShape.SizeBDiagCursor,  # VTK_CURSOR_SIZENE
        3: Qt.CursorShape.SizeFDiagCursor,  # VTK_CURSOR_SIZENWSE
        4: Qt.CursorShape.SizeBDiagCursor,  # VTK_CURSOR_SIZESW
        5: Qt.CursorShape.SizeFDiagCursor,  # VTK_CURSOR_SIZESE
        6: Qt.CursorShape.SizeVerCursor,  # VTK_CURSOR_SIZENS
        7: Qt.CursorShape.SizeHorCursor,  # VTK_CURSOR_SIZEWE
        8: Qt.CursorShape.SizeAllCursor,  # VTK_CURSOR_SIZEALL
        9: Qt.CursorShape.PointingHandCursor,  # VTK_CURSOR_HAND
        10: Qt.CursorShape.CrossCursor,  # VTK_CURSOR_CROSSHAIR
    }

    def __init__(self, parent=None, **kw):
        """Initialize the widget and its render window (``rw``/``iren`` kwargs)."""
        # The GL format must be set as the process-wide default: a per-widget
        # ``setFormat`` makes the widget's context incompatible with the
        # top-level window's share context on Wayland and the widget then
        # composites black (verified: even a plain magenta-clearing
        # QOpenGLWidget breaks with per-widget setFormat there). Setting the
        # default is effective as long as the top-level window has not been
        # created yet, so this works even when the user already made the
        # QApplication. Same requirement as C++ QVTKOpenGLNativeWidget.
        QSurfaceFormat.setDefaultFormat(_default_format())
        QOpenGLWidget.__init__(self, parent)
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
        self.setMouseTracking(True)  # get all mouse events
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))

        rw = kw.get("rw")
        self._RenderWindow = rw if rw is not None else vtkGenericOpenGLRenderWindow()
        self._RenderWindow.SetReadyForRendering(False)
        self._RenderWindow.SetFrameBlitModeToNoBlit()

        iren = kw.get("iren")
        self._Iren = iren if iren is not None else vtkGenericRenderWindowInteractor()
        # SetRenderWindow also does RenderWindow.SetInteractor(iren)
        self._Iren.SetRenderWindow(self._RenderWindow)

        # Captured in initializeGL; used to service WindowMakeCurrentEvent.
        self._ctx = None
        self._surface = None
        self._gl = None
        self._in_paint = False  # C++ InPaint

        # input-event state (ported from VTK's QVTKRenderWindowInteractor.py)
        self._active_button = Qt.MouseButton.NoButton
        self._save_x = 0
        self._save_y = 0
        self._save_modifiers = Qt.KeyboardModifier.NoModifier
        self._wheel_delta = 0

        self._RenderWindow.AddObserver("WindowMakeCurrentEvent", self._cb_make_current)  # ty: ignore[invalid-argument-type]
        self._RenderWindow.AddObserver("WindowIsCurrentEvent", self._cb_is_current)  # ty: ignore[invalid-argument-type]
        self._RenderWindow.AddObserver("WindowFrameEvent", self._cb_frame)  # ty: ignore[invalid-argument-type]
        self._RenderWindow.AddObserver("CursorChangedEvent", self.CursorChangedEvent)  # ty: ignore[invalid-argument-type]

        # VTK interactor timers (vtkGenericRenderWindowInteractor delegates).
        self._Timer = QTimer(self)
        self._Timer.timeout.connect(self.TimerEvent)
        self._Iren.AddObserver("CreateTimerEvent", self.CreateTimer)  # ty: ignore[invalid-argument-type]
        self._Iren.AddObserver("DestroyTimerEvent", self.DestroyTimer)  # ty: ignore[invalid-argument-type]

        # If we've a parent, it does not close the child when closed.
        # Connect the parent's destroyed signal to this widget's close
        # slot for proper cleanup of VTK objects.
        qparent = self.parent()
        if qparent is not None:
            qparent.destroyed.connect(self.close, Qt.ConnectionType.DirectConnection)

    # ---- render-window observers (QVTKRenderWindowAdapter) -------------------
    def _cb_make_current(self, obj, evt):
        """Make VTK's context current WITHOUT touching framebuffer bindings."""
        if self._ctx is not None and self._surface is not None:
            self._ctx.makeCurrent(self._surface)

    def _cb_is_current(self, obj, evt):
        # The bool* calldata is not reachable from Python; write the answer
        # into the member the event reads back via SetIsCurrent.
        rw = self._RenderWindow
        if rw is None:
            return
        cur = QOpenGLContext.currentContext()
        rw.SetIsCurrent(self._ctx is not None and cur is self._ctx)

    def _cb_frame(self, obj, evt):
        """Schedule the blit of a just-finished VTK render to the widget."""
        rw = self._RenderWindow
        if rw is None:
            return
        if rw.GetDoubleBuffer() and not rw.GetSwapBuffers():
            # rendered to the back buffer only: not meant to be shown yet
            return
        if not self._in_paint:
            self.update()

    def _set_symbol_loader(self):
        """Point VTK's GL loader at the platform's getProcAddress."""
        with contextlib.suppress(Exception):
            app = cast("QApplication | None", QApplication.instance())
            if app is None:
                return
            pname = app.platformName()
            if pname.startswith("wayland"):
                lib = ctypes.CDLL("libEGL.so.1")
                gpa = ctypes.cast(lib.eglGetProcAddress, ctypes.c_void_p).value
            else:
                lib = ctypes.CDLL("libGL.so.1")
                gpa = ctypes.cast(lib.glXGetProcAddressARB, ctypes.c_void_p).value
            self._RenderWindow.SetOpenGLSymbolLoader2(int(gpa or 0), 0)

    # ---- QOpenGLWidget overrides ---------------------------------------------
    def initializeGL(self):
        super().initializeGL()
        rw = self._RenderWindow
        if rw is None:
            return
        self._ctx = self.context()
        self._surface = self._ctx.surface()
        self._gl = _GLAPI(self._ctx)
        # Connections die with the context object, so a plain connect cannot
        # duplicate across context re-creation.
        self._ctx.aboutToBeDestroyed.connect(self._cleanup_context)
        # GetInitialized is not wrapped on VTK < 9.3; fall back to always
        # (re-)initializing there, which VTK's internal guards make a no-op.
        get_initialized = getattr(rw, "GetInitialized", None)
        if get_initialized is None or not get_initialized():
            self._set_symbol_loader()
            # Load the GL function pointers before OpenGLInit: on VTK <= 9.5,
            # vtkGenericOpenGLRenderWindow::OpenGLInit resets the GL state
            # cache (raw glGet* calls) BEFORE initializing the context, which
            # segfaults on unloaded function pointers. VTK >= 9.6 initializes
            # the context first itself, and this extra call is then a no-op.
            rw.OpenGLInitContext()
            rw.OpenGLInit()
        # Qt leaves depth testing off and GL_LESS; VTK expects GL_LEQUAL.
        st = rw.GetState()
        st.Reset()
        st.vtkglDepthFunc(GL_LEQUAL)
        st.vtkglEnable(GL_DEPTH_TEST)
        rw.SetForceMaximumHardwareLineWidth(1)
        rw.SetReadyForRendering(True)
        rw.SetOwnContext(0)
        rw.OpenGLInitContext()

    def _cleanup_context(self):
        """Release VTK's GL resources before the Qt context is destroyed."""
        # Qt's canonical aboutToBeDestroyed pattern: the slot itself must make
        # the (still alive) context current before releasing GL resources,
        # otherwise the driver frees objects against whatever context happens
        # to be current -- heap corruption that crashes much later.
        if self._ctx is not None and self._surface is not None:
            with contextlib.suppress(Exception):
                self._ctx.makeCurrent(self._surface)
        rw = self._RenderWindow
        if rw is not None:
            rw.Finalize()
            rw.SetReadyForRendering(False)
        self._ctx = None
        self._surface = None
        self._gl = None

    def resizeGL(self, w, h):
        # QVTKRenderWindowAdapter::resize: VTK works in device pixels.
        rw = self._RenderWindow
        if rw is None:
            return
        dpr = self.devicePixelRatioF()
        dw = max(1, round(w * dpr))
        dh = max(1, round(h * dpr))
        iren = rw.GetInteractor()
        if iren is not None:
            iren.UpdateSize(dw, dh)
            iren.InvokeEvent("ConfigureEvent")
        else:
            rw.SetSize(dw, dh)
        # NOTE: no self.screen()/SetScreenSize here. VTK only uses the screen
        # size for fullscreen render windows (not applicable to a widget), and
        # PySide's wrapper for QWidget.screen() can end up owning -- and later
        # deleting -- the application's QScreen, crashing on next screen use.
        rw.SetDPI(round(72 * dpr))

    def paintGL(self):
        super().paintGL()
        rw = self._RenderWindow
        if rw is None or not rw.GetReadyForRendering():
            if self._gl is not None:  # no render window: fill with white (C++ parity)
                self._gl.glClearColor(1.0, 1.0, 1.0, 1.0)
                self._gl.glClear(GL_COLOR_BUFFER_BIT)
            return
        st = rw.GetState()
        st.Reset()  # Qt touched GL since the last VTK call: resync the cache
        st.Push()
        st.vtkglDepthFunc(GL_LEQUAL)
        # Unlike C++ QVTKOpenGLNativeWidget (which skips the VTK render when the
        # paint was scheduled by a finished render's WindowFrameEvent), always
        # render: pyvista mutates the scene (cameras, actors) without asking the
        # widget to repaint, so a skipped render here shows a stale frame. This
        # matches the vendored QVTKRenderWindowInteractor's paintEvent behavior.
        if not self._in_paint:
            self._in_paint = True
            try:
                iren = rw.GetInteractor()
                if iren is not None:
                    iren.Render()
                else:
                    rw.Render()
            finally:
                self._in_paint = False
        # Rendering may change the current context (progress events triggering
        # other widgets): restore the widget's context AND backing FBO binding.
        self.makeCurrent()
        dpr = self.devicePixelRatioF()
        rect = QRect(0, 0, max(1, round(self.width() * dpr)), max(1, round(self.height() * dpr)))
        self._blit(self.defaultFramebufferObject(), rect)
        st.Pop()

    # ---- QVTKRenderWindowAdapter::blit + clearAlpha ---------------------------
    def _blit(self, target_id, rect):
        rw = self._RenderWindow
        f = self._gl
        if rw is None or f is None:
            return
        f.glBindFramebuffer(GL_DRAW_FRAMEBUFFER, target_id)
        f.draw_buffer_attachment0()
        scissor = bool(f.glIsEnabled(GL_SCISSOR_TEST))
        if scissor:  # scissor affects glBlitFramebuffer
            rw.GetState().vtkglDisable(GL_SCISSOR_TEST)
            f.glDisable(GL_SCISSOR_TEST)
        w, h = rw.GetSize()
        # Blits VTK's display framebuffer into the currently bound draw FBO;
        # only the read binding is pushed/popped internally.
        rw.BlitDisplayFramebuffer(0, 0, 0, w, h, rect.x(), rect.y(), rect.width(), rect.height(), GL_COLOR_BUFFER_BIT, GL_LINEAR)
        # clearAlpha: alpha < 1 makes compositors blend the window with what is
        # behind it. The raw-GL state dirt is healed by the state Reset that
        # both paintGL and vtkGenericOpenGLRenderWindow::Render perform.
        f.glColorMask(False, False, False, True)
        f.glClearColor(0.0, 0.0, 0.0, 1.0)
        f.glViewport(rect.x(), rect.y(), rect.width(), rect.height())
        f.glClear(GL_COLOR_BUFFER_BIT)
        f.glColorMask(True, True, True, True)
        if scissor:
            rw.GetState().vtkglEnable(GL_SCISSOR_TEST)
            f.glEnable(GL_SCISSOR_TEST)

    # ---- interface expected by QtInteractor / pyvista -------------------------
    def __getattr__(self, attr):
        """Behave like the vtkGenericRenderWindowInteractor for unknown attrs."""
        iren = self.__dict__.get("_Iren")
        if iren is not None and hasattr(iren, attr):
            return getattr(iren, attr)
        msg = f"{type(self).__name__} has no attribute {attr!r}"
        raise AttributeError(msg)

    def GetRenderWindow(self):
        return self._RenderWindow

    def Render(self):
        self.update()

    def Finalize(self):
        rw = self._RenderWindow
        if rw is not None:
            rw.Finalize()

    def CreateTimer(self, obj, evt):
        self._Timer.start(10)

    def DestroyTimer(self, obj, evt):
        self._Timer.stop()
        return 1

    def TimerEvent(self):
        iren = self.__dict__.get("_Iren")
        if iren is not None and hasattr(iren, "TimerEvent"):
            iren.TimerEvent()

    def closeEvent(self, evt):
        # No explicit makeCurrent here: Finalize's GL teardown drives the
        # render window's own MakeCurrent (serviced by _cb_make_current), and
        # QOpenGLWidget.makeCurrent on a widget whose window is being torn
        # down (parent destroyed -> close) is unsafe.
        self.Finalize()

    def sizeHint(self):
        return QSize(400, 400)

    # ---- cursor plumbing (from VTK's QVTKRenderWindowInteractor.py) ----------
    def CursorChangedEvent(self, obj, evt):
        """Handle CursorChangedEvent fired by the render window."""
        # Deferred: when the event fires the current cursor is not yet set.
        QTimer.singleShot(0, self.ShowCursor)

    def HideCursor(self):
        self.setCursor(Qt.CursorShape.BlankCursor)

    def ShowCursor(self):
        rw = self._RenderWindow
        if rw is None:
            return
        vtk_cursor = rw.GetCurrentCursor()
        qt_cursor = self._CURSOR_MAP.get(vtk_cursor, Qt.CursorShape.ArrowCursor)
        self.setCursor(qt_cursor)

    # ---- input events (from VTK's QVTKRenderWindowInteractor.py) -------------
    def _GetKeyCharAndKeySym(self, ev):
        """Convert a Qt key event into a char and a vtk keysym."""
        # if there is a char, convert its ASCII code to a VTK keysym
        try:
            key_char = ev.text()[0]
            key_sym = _KEYSYMS_FOR_ASCII[ord(key_char)]
        except IndexError:
            key_char = "\0"
            key_sym = None
        # next, try converting the Qt key code to a VTK keysym
        if key_sym is None:
            key_sym = _KEYSYMS.get(ev.key())
        # use "None" as a fallback
        if key_sym is None:
            key_sym = "None"
        return key_char, key_sym

    def _GetCtrlShift(self, ev):
        ctrl = shift = False
        modifiers = ev.modifiers() if hasattr(ev, "modifiers") else self._save_modifiers
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            shift = True
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            ctrl = True
        return ctrl, shift

    def _setEventInformation(self, x, y, ctrl, shift, key, repeat=0, keysum=None):  # noqa: PLR0913
        # VTK's y axis points up and coordinates are in device pixels.
        scale = self.devicePixelRatioF()
        self._Iren.SetEventInformation(
            round(x * scale),
            round((self.height() - y - 1) * scale),
            ctrl,
            shift,
            key,
            repeat,
            keysum,  # ty: ignore[invalid-argument-type]  # stubs reject None (nullptr is fine)
        )

    def enterEvent(self, ev):
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(self._save_x, self._save_y, ctrl, shift, chr(0), 0, None)
        self._Iren.EnterEvent()

    def leaveEvent(self, ev):
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(self._save_x, self._save_y, ctrl, shift, chr(0), 0, None)
        self._Iren.LeaveEvent()

    def mousePressEvent(self, ev):
        ctrl, shift = self._GetCtrlShift(ev)
        repeat = 1 if ev.type() == QEvent.Type.MouseButtonDblClick else 0
        x, y = _get_event_pos(ev)
        self._setEventInformation(x, y, ctrl, shift, chr(0), repeat, None)
        self._active_button = ev.button()
        if self._active_button == Qt.MouseButton.LeftButton:
            self._Iren.LeftButtonPressEvent()
        elif self._active_button == Qt.MouseButton.RightButton:
            self._Iren.RightButtonPressEvent()
        elif self._active_button == Qt.MouseButton.MiddleButton:
            self._Iren.MiddleButtonPressEvent()

    def mouseReleaseEvent(self, ev):
        ctrl, shift = self._GetCtrlShift(ev)
        x, y = _get_event_pos(ev)
        self._setEventInformation(x, y, ctrl, shift, chr(0), 0, None)
        if self._active_button == Qt.MouseButton.LeftButton:
            self._Iren.LeftButtonReleaseEvent()
        elif self._active_button == Qt.MouseButton.RightButton:
            self._Iren.RightButtonReleaseEvent()
        elif self._active_button == Qt.MouseButton.MiddleButton:
            self._Iren.MiddleButtonReleaseEvent()

    def mouseMoveEvent(self, ev):
        self._save_modifiers = ev.modifiers()
        x, y = _get_event_pos(ev)
        self._save_x = x
        self._save_y = y
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(x, y, ctrl, shift, chr(0), 0, None)
        self._Iren.MouseMoveEvent()

    def keyPressEvent(self, ev):
        key, key_sym = self._GetKeyCharAndKeySym(ev)
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(self._save_x, self._save_y, ctrl, shift, key, 0, key_sym)
        self._Iren.KeyPressEvent()
        self._Iren.CharEvent()

    def keyReleaseEvent(self, ev):
        key, key_sym = self._GetKeyCharAndKeySym(ev)
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(self._save_x, self._save_y, ctrl, shift, key, 0, key_sym)
        self._Iren.KeyReleaseEvent()

    def wheelEvent(self, ev):
        if hasattr(ev, "delta"):  # Qt4 compat kept from the vendored source
            self._wheel_delta += ev.delta()
        else:
            self._wheel_delta += ev.angleDelta().y()
        if self._wheel_delta >= 120:
            self._Iren.MouseWheelForwardEvent()
            self._wheel_delta = 0
        elif self._wheel_delta <= -120:
            self._Iren.MouseWheelBackwardEvent()
            self._wheel_delta = 0


# keysym tables from VTK's QVTKRenderWindowInteractor.py
_KEYSYMS_FOR_ASCII = (
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    "Tab",
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    "space",
    "exclam",
    "quotedbl",
    "numbersign",
    "dollar",
    "percent",
    "ampersand",
    "quoteright",
    "parenleft",
    "parenright",
    "asterisk",
    "plus",
    "comma",
    "minus",
    "period",
    "slash",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "colon",
    "semicolon",
    "less",
    "equal",
    "greater",
    "question",
    "at",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "bracketleft",
    "backslash",
    "bracketright",
    "asciicircum",
    "underscore",
    "quoteleft",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "braceleft",
    "bar",
    "braceright",
    "asciitilde",
    "Delete",
)

_KEYSYMS = {
    Qt.Key.Key_Backspace: "BackSpace",
    Qt.Key.Key_Tab: "Tab",
    Qt.Key.Key_Backtab: "Tab",
    # Qt.Key.Key_Clear : 'Clear',
    Qt.Key.Key_Return: "Return",
    Qt.Key.Key_Enter: "Return",
    Qt.Key.Key_Shift: "Shift_L",
    Qt.Key.Key_Control: "Control_L",
    Qt.Key.Key_Alt: "Alt_L",
    Qt.Key.Key_Pause: "Pause",
    Qt.Key.Key_CapsLock: "Caps_Lock",
    Qt.Key.Key_Escape: "Escape",
    Qt.Key.Key_Space: "space",
    # Qt.Key.Key_Prior : 'Prior',
    # Qt.Key.Key_Next : 'Next',
    Qt.Key.Key_End: "End",
    Qt.Key.Key_Home: "Home",
    Qt.Key.Key_Left: "Left",
    Qt.Key.Key_Up: "Up",
    Qt.Key.Key_Right: "Right",
    Qt.Key.Key_Down: "Down",
    Qt.Key.Key_SysReq: "Snapshot",
    Qt.Key.Key_Insert: "Insert",
    Qt.Key.Key_Delete: "Delete",
    Qt.Key.Key_Help: "Help",
    Qt.Key.Key_0: "0",
    Qt.Key.Key_1: "1",
    Qt.Key.Key_2: "2",
    Qt.Key.Key_3: "3",
    Qt.Key.Key_4: "4",
    Qt.Key.Key_5: "5",
    Qt.Key.Key_6: "6",
    Qt.Key.Key_7: "7",
    Qt.Key.Key_8: "8",
    Qt.Key.Key_9: "9",
    Qt.Key.Key_A: "a",
    Qt.Key.Key_B: "b",
    Qt.Key.Key_C: "c",
    Qt.Key.Key_D: "d",
    Qt.Key.Key_E: "e",
    Qt.Key.Key_F: "f",
    Qt.Key.Key_G: "g",
    Qt.Key.Key_H: "h",
    Qt.Key.Key_I: "i",
    Qt.Key.Key_J: "j",
    Qt.Key.Key_K: "k",
    Qt.Key.Key_L: "l",
    Qt.Key.Key_M: "m",
    Qt.Key.Key_N: "n",
    Qt.Key.Key_O: "o",
    Qt.Key.Key_P: "p",
    Qt.Key.Key_Q: "q",
    Qt.Key.Key_R: "r",
    Qt.Key.Key_S: "s",
    Qt.Key.Key_T: "t",
    Qt.Key.Key_U: "u",
    Qt.Key.Key_V: "v",
    Qt.Key.Key_W: "w",
    Qt.Key.Key_X: "x",
    Qt.Key.Key_Y: "y",
    Qt.Key.Key_Z: "z",
    Qt.Key.Key_Asterisk: "asterisk",
    Qt.Key.Key_Plus: "plus",
    Qt.Key.Key_Minus: "minus",
    Qt.Key.Key_Period: "period",
    Qt.Key.Key_Slash: "slash",
    Qt.Key.Key_F1: "F1",
    Qt.Key.Key_F2: "F2",
    Qt.Key.Key_F3: "F3",
    Qt.Key.Key_F4: "F4",
    Qt.Key.Key_F5: "F5",
    Qt.Key.Key_F6: "F6",
    Qt.Key.Key_F7: "F7",
    Qt.Key.Key_F8: "F8",
    Qt.Key.Key_F9: "F9",
    Qt.Key.Key_F10: "F10",
    Qt.Key.Key_F11: "F11",
    Qt.Key.Key_F12: "F12",
    Qt.Key.Key_F13: "F13",
    Qt.Key.Key_F14: "F14",
    Qt.Key.Key_F15: "F15",
    Qt.Key.Key_F16: "F16",
    Qt.Key.Key_F17: "F17",
    Qt.Key.Key_F18: "F18",
    Qt.Key.Key_F19: "F19",
    Qt.Key.Key_F20: "F20",
    Qt.Key.Key_F21: "F21",
    Qt.Key.Key_F22: "F22",
    Qt.Key.Key_F23: "F23",
    Qt.Key.Key_F24: "F24",
    Qt.Key.Key_NumLock: "Num_Lock",
    Qt.Key.Key_ScrollLock: "Scroll_Lock",
}
