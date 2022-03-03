# modified from: https://gitlab.kitware.com/vtk/vtk
# under the OSI-approved BSD 3-clause License
# TODO: Mayavi has a potentially different version that might be better or worse
# coding=utf-8
"""
A simple VTK widget for PyQt or PySide.
See http://www.trolltech.com for Qt documentation,
http://www.riverbankcomputing.co.uk for PyQt, and
http://pyside.github.io for PySide.

This class is based on the vtkGenericRenderWindowInteractor and is
therefore fairly powerful.  It should also play nicely with the
vtk3DWidget code.

Created by Prabhu Ramachandran, May 2002
Based on David Gobbi's QVTKRenderWidget.py

Changes by Gerard Vermeulen Feb. 2003
 Win32 support.

Changes by Gerard Vermeulen, May 2003
 Bug fixes and better integration with the Qt framework.

Changes by Phil Thompson, Nov. 2006
 Ported to PyQt v4.
 Added support for wheel events.

Changes by Phil Thompson, Oct. 2007
 Bug fixes.

Changes by Phil Thompson, Mar. 2008
 Added cursor support.

Changes by Rodrigo Mologni, Sep. 2013 (Credit to Daniele Esposti)
 Bug fix to PySide: Converts PyCObject to void pointer.

Changes by Greg Schussman, Aug. 2014
 The keyPressEvent function now passes keysym instead of None.

Changes by Alex Tsui, Apr. 2015
 Port from PyQt4 to PyQt5.

Changes by Fabian Wenzel, Jan. 2016
 Support for Python3

Changes by Tobias Hänel, Sep. 2018
 Support for PySide2

Changes by Ruben de Bruin, Aug. 2019
 Fixes to the keyPressEvent function

Changes by Chen Jintao, Aug. 2021
 Support for PySide6
"""

# Check whether a specific PyQt implementation was chosen
try:
    import vtkmodules.qt
    PyQtImpl = vtkmodules.qt.PyQtImpl
except ImportError:
    pass

# Check whether a specific QVTKRenderWindowInteractor base
# class was chosen, can be set to "QGLWidget" in
# PyQt implementation version lower than Pyside6,
# or "QOpenGLWidget" in Pyside6
QVTKRWIBase = "QWidget"
try:
    import vtkmodules.qt
    QVTKRWIBase = vtkmodules.qt.QVTKRWIBase
except ImportError:
    pass

from vtkmodules.vtkRenderingCore import vtkRenderWindow
from vtkmodules.vtkRenderingUI import vtkGenericRenderWindowInteractor

if PyQtImpl is None:
    # Autodetect the PyQt implementation to use
    try:
        import PyQt6
        PyQtImpl = "PyQt6"
    except ImportError:
        try:
            import PySide6
            PyQtImpl = "PySide6"
        except ImportError:
            try:
                import PyQt5
                PyQtImpl = "PyQt5"
            except ImportError:
                try:
                    import PySide2
                    PyQtImpl = "PySide2"
                except ImportError:
                    try:
                        import PyQt4
                        PyQtImpl = "PyQt4"
                    except ImportError:
                        try:
                            import PySide
                            PyQtImpl = "PySide"
                        except ImportError:
                            raise ImportError("Cannot load either PyQt or PySide")

# Check the compatibility of PyQtImpl and QVTKRWIBase
if QVTKRWIBase != "QWidget":
    if PyQtImpl in ["PyQt6", "PySide6"] and QVTKRWIBase == "QOpenGLWidget":
        pass  # compatible
    elif PyQtImpl in ["PyQt5", "PySide2","PyQt4", "PySide"] and QVTKRWIBase == "QGLWidget":
        pass  # compatible
    else:
        raise ImportError("Cannot load " + QVTKRWIBase + " from " + PyQtImpl)

if PyQtImpl == "PyQt6":
    if QVTKRWIBase == "QOpenGLWidget":
        from PyQt6.QtOpenGLWidgets import QOpenGLWidget
    from PyQt6.QtWidgets import QWidget
    from PyQt6.QtWidgets import QSizePolicy
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtWidgets import QMainWindow
    from PyQt6.QtGui import QCursor
    from PyQt6.QtCore import Qt
    from PyQt6.QtCore import QTimer
    from PyQt6.QtCore import QObject
    from PyQt6.QtCore import QSize
    from PyQt6.QtCore import QEvent
elif PyQtImpl == "PySide6":
    if QVTKRWIBase == "QOpenGLWidget":
        from PySide6.QtOpenGLWidgets import QOpenGLWidget
    from PySide6.QtWidgets import QWidget
    from PySide6.QtWidgets import QSizePolicy
    from PySide6.QtWidgets import QApplication
    from PySide6.QtWidgets import QMainWindow
    from PySide6.QtGui import QCursor
    from PySide6.QtCore import Qt
    from PySide6.QtCore import QTimer
    from PySide6.QtCore import QObject
    from PySide6.QtCore import QSize
    from PySide6.QtCore import QEvent
elif PyQtImpl == "PyQt5":
    if QVTKRWIBase == "QGLWidget":
        from PyQt5.QtOpenGL import QGLWidget
    from PyQt5.QtWidgets import QWidget
    from PyQt5.QtWidgets import QSizePolicy
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtWidgets import QMainWindow
    from PyQt5.QtGui import QCursor
    from PyQt5.QtCore import Qt
    from PyQt5.QtCore import QTimer
    from PyQt5.QtCore import QObject
    from PyQt5.QtCore import QSize
    from PyQt5.QtCore import QEvent
elif PyQtImpl == "PySide2":
    if QVTKRWIBase == "QGLWidget":
        from PySide2.QtOpenGL import QGLWidget
    from PySide2.QtWidgets import QWidget
    from PySide2.QtWidgets import QSizePolicy
    from PySide2.QtWidgets import QApplication
    from PySide2.QtWidgets import QMainWindow
    from PySide2.QtGui import QCursor
    from PySide2.QtCore import Qt
    from PySide2.QtCore import QTimer
    from PySide2.QtCore import QObject
    from PySide2.QtCore import QSize
    from PySide2.QtCore import QEvent
elif PyQtImpl == "PyQt4":
    if QVTKRWIBase == "QGLWidget":
        from PyQt4.QtOpenGL import QGLWidget
    from PyQt4.QtGui import QWidget
    from PyQt4.QtGui import QSizePolicy
    from PyQt4.QtGui import QApplication
    from PyQt4.QtGui import QMainWindow
    from PyQt4.QtCore import Qt
    from PyQt4.QtCore import QTimer
    from PyQt4.QtCore import QObject
    from PyQt4.QtCore import QSize
    from PyQt4.QtCore import QEvent
elif PyQtImpl == "PySide":
    if QVTKRWIBase == "QGLWidget":
        from PySide.QtOpenGL import QGLWidget
    from PySide.QtGui import QWidget
    from PySide.QtGui import QSizePolicy
    from PySide.QtGui import QApplication
    from PySide.QtGui import QMainWindow
    from PySide.QtCore import Qt
    from PySide.QtCore import QTimer
    from PySide.QtCore import QObject
    from PySide.QtCore import QSize
    from PySide.QtCore import QEvent
else:
    raise ImportError("Unknown PyQt implementation " + repr(PyQtImpl))

# Define types for base class, based on string
if QVTKRWIBase == "QWidget":
    QVTKRWIBaseClass = QWidget
elif QVTKRWIBase == "QGLWidget":
    QVTKRWIBaseClass = QGLWidget
elif QVTKRWIBase == "QOpenGLWidget":
    QVTKRWIBaseClass = QOpenGLWidget
else:
    raise ImportError("Unknown base class for QVTKRenderWindowInteractor " + QVTKRWIBase)

class QVTKRenderWindowInteractor(QVTKRWIBaseClass):

    """ A QVTKRenderWindowInteractor for Python and Qt.  Uses a
    vtkGenericRenderWindowInteractor to handle the interactions.  Use
    GetRenderWindow() to get the vtkRenderWindow.  Create with the
    keyword stereo=1 in order to generate a stereo-capable window.

    The user interface is summarized in vtkInteractorStyle.h:

    - Keypress j / Keypress t: toggle between joystick (position
    sensitive) and trackball (motion sensitive) styles. In joystick
    style, motion occurs continuously as long as a mouse button is
    pressed. In trackball style, motion occurs when the mouse button
    is pressed and the mouse pointer moves.

    - Keypress c / Keypress o: toggle between camera and object
    (actor) modes. In camera mode, mouse events affect the camera
    position and focal point. In object mode, mouse events affect
    the actor that is under the mouse pointer.

    - Button 1: rotate the camera around its focal point (if camera
    mode) or rotate the actor around its origin (if actor mode). The
    rotation is in the direction defined from the center of the
    renderer's viewport towards the mouse position. In joystick mode,
    the magnitude of the rotation is determined by the distance the
    mouse is from the center of the render window.

    - Button 2: pan the camera (if camera mode) or translate the actor
    (if object mode). In joystick mode, the direction of pan or
    translation is from the center of the viewport towards the mouse
    position. In trackball mode, the direction of motion is the
    direction the mouse moves. (Note: with 2-button mice, pan is
    defined as <Shift>-Button 1.)

    - Button 3: zoom the camera (if camera mode) or scale the actor
    (if object mode). Zoom in/increase scale if the mouse position is
    in the top half of the viewport; zoom out/decrease scale if the
    mouse position is in the bottom half. In joystick mode, the amount
    of zoom is controlled by the distance of the mouse pointer from
    the horizontal centerline of the window.

    - Keypress 3: toggle the render window into and out of stereo
    mode.  By default, red-blue stereo pairs are created. Some systems
    support Crystal Eyes LCD stereo glasses; you have to invoke
    SetStereoTypeToCrystalEyes() on the rendering window.  Note: to
    use stereo you also need to pass a stereo=1 keyword argument to
    the constructor.

    - Keypress e: exit the application.

    - Keypress f: fly to the picked point

    - Keypress p: perform a pick operation. The render window interactor
    has an internal instance of vtkCellPicker that it uses to pick.

    - Keypress r: reset the camera view along the current view
    direction. Centers the actors and moves the camera so that all actors
    are visible.

    - Keypress s: modify the representation of all actors so that they
    are surfaces.

    - Keypress u: invoke the user-defined function. Typically, this
    keypress will bring up an interactor that you can type commands in.

    - Keypress w: modify the representation of all actors so that they
    are wireframe.
    """

    # Map between VTK and Qt cursors.
    _CURSOR_MAP = {
        0:  Qt.ArrowCursor,          # VTK_CURSOR_DEFAULT
        1:  Qt.ArrowCursor,          # VTK_CURSOR_ARROW
        2:  Qt.SizeBDiagCursor,      # VTK_CURSOR_SIZENE
        3:  Qt.SizeFDiagCursor,      # VTK_CURSOR_SIZENWSE
        4:  Qt.SizeBDiagCursor,      # VTK_CURSOR_SIZESW
        5:  Qt.SizeFDiagCursor,      # VTK_CURSOR_SIZESE
        6:  Qt.SizeVerCursor,        # VTK_CURSOR_SIZENS
        7:  Qt.SizeHorCursor,        # VTK_CURSOR_SIZEWE
        8:  Qt.SizeAllCursor,        # VTK_CURSOR_SIZEALL
        9:  Qt.PointingHandCursor,   # VTK_CURSOR_HAND
        10: Qt.CrossCursor,          # VTK_CURSOR_CROSSHAIR
    }

    def __init__(self, parent=None, **kw):
        # the current button
        self._ActiveButton = Qt.NoButton

        # private attributes
        self.__saveX = 0
        self.__saveY = 0
        self.__saveModifiers = Qt.NoModifier
        self.__saveButtons = Qt.NoButton
        self.__wheelDelta = 0

        # do special handling of some keywords:
        # stereo, rw

        try:
            stereo = bool(kw['stereo'])
        except KeyError:
            stereo = False

        try:
            rw = kw['rw']
        except KeyError:
            rw = None

        # create base qt-level widget
        if QVTKRWIBase == "QWidget":
            if "wflags" in kw:
                wflags = kw['wflags']
            else:
                wflags = Qt.WindowType.Widget
            QWidget.__init__(self, parent, wflags | Qt.MSWindowsOwnDC)
        elif QVTKRWIBase == "QGLWidget":
            QGLWidget.__init__(self, parent)
        elif QVTKRWIBase == "QOpenGLWidget":
            QOpenGLWidget.__init__(self, parent)

        if rw: # user-supplied render window
            self._RenderWindow = rw
        else:
            self._RenderWindow = vtkRenderWindow()

        WId = self.winId()

        # Python2
        if type(WId).__name__ == 'PyCObject':
            from ctypes import pythonapi, c_void_p, py_object

            pythonapi.PyCObject_AsVoidPtr.restype  = c_void_p
            pythonapi.PyCObject_AsVoidPtr.argtypes = [py_object]

            WId = pythonapi.PyCObject_AsVoidPtr(WId)

        # Python3
        elif type(WId).__name__ == 'PyCapsule':
            from ctypes import pythonapi, c_void_p, py_object, c_char_p

            pythonapi.PyCapsule_GetName.restype = c_char_p
            pythonapi.PyCapsule_GetName.argtypes = [py_object]

            name = pythonapi.PyCapsule_GetName(WId)

            pythonapi.PyCapsule_GetPointer.restype  = c_void_p
            pythonapi.PyCapsule_GetPointer.argtypes = [py_object, c_char_p]

            WId = pythonapi.PyCapsule_GetPointer(WId, name)

        self._RenderWindow.SetWindowInfo(str(int(WId)))

        if stereo: # stereo mode
            self._RenderWindow.StereoCapableWindowOn()
            self._RenderWindow.SetStereoTypeToCrystalEyes()

        try:
            self._Iren = kw['iren']
        except KeyError:
            self._Iren = vtkGenericRenderWindowInteractor()
            self._Iren.SetRenderWindow(self._RenderWindow)

        # do all the necessary qt setup
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_PaintOnScreen)
        self.setMouseTracking(True) # get all mouse events
        self.setFocusPolicy(Qt.WheelFocus)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

        self._Timer = QTimer(self)
        self._Timer.timeout.connect(self.TimerEvent)

        self._Iren.AddObserver('CreateTimerEvent', self.CreateTimer)
        self._Iren.AddObserver('DestroyTimerEvent', self.DestroyTimer)
        self._Iren.GetRenderWindow().AddObserver('CursorChangedEvent',
                                                 self.CursorChangedEvent)

        # If we've a parent, it does not close the child when closed.
        # Connect the parent's destroyed signal to this widget's close
        # slot for proper cleanup of VTK objects.
        if self.parent():
            self.parent().destroyed.connect(self.close, Qt.DirectConnection)

    def __getattr__(self, attr):
        """Makes the object behave like a vtkGenericRenderWindowInteractor"""
        if attr == '__vtk__':
            return lambda t=self._Iren: t
        elif hasattr(self._Iren, attr):
            return getattr(self._Iren, attr)
        else:
            raise AttributeError(self.__class__.__name__ +
                  " has no attribute named " + attr)

    def Finalize(self):
        '''
        Call internal cleanup method on VTK objects
        '''
        self._RenderWindow.Finalize()

    def CreateTimer(self, obj, evt):
        self._Timer.start(10)

    def DestroyTimer(self, obj, evt):
        self._Timer.stop()
        return 1

    def TimerEvent(self):
        self._Iren.TimerEvent()

    def CursorChangedEvent(self, obj, evt):
        """Called when the CursorChangedEvent fires on the render window."""
        # This indirection is needed since when the event fires, the current
        # cursor is not yet set so we defer this by which time the current
        # cursor should have been set.
        QTimer.singleShot(0, self.ShowCursor)

    def HideCursor(self):
        """Hides the cursor."""
        self.setCursor(Qt.BlankCursor)

    def ShowCursor(self):
        """Shows the cursor."""
        vtk_cursor = self._Iren.GetRenderWindow().GetCurrentCursor()
        qt_cursor = self._CURSOR_MAP.get(vtk_cursor, Qt.ArrowCursor)
        self.setCursor(qt_cursor)

    def closeEvent(self, evt):
        self.Finalize()

    def sizeHint(self):
        return QSize(400, 400)

    def paintEngine(self):
        return None

    def paintEvent(self, ev):
        self._Iren.Render()

    def resizeEvent(self, ev):
        scale = self._getPixelRatio()
        w = int(round(scale*self.width()))
        h = int(round(scale*self.height()))
        self._RenderWindow.SetDPI(int(round(72*scale)))
        vtkRenderWindow.SetSize(self._RenderWindow, w, h)
        self._Iren.SetSize(w, h)
        self._Iren.ConfigureEvent()
        self.update()

    def _GetKeyCharAndKeySym(self, ev):
        """ Convert a Qt key into a char and a vtk keysym.

        This is essentially copied from the c++ implementation in
        GUISupport/Qt/QVTKInteractorAdapter.cxx.
        """
        # if there is a char, convert its ASCII code to a VTK keysym
        try:
            keyChar = ev.text()[0]
            keySym = _keysyms_for_ascii[ord(keyChar)]
        except IndexError:
            keyChar = '\0'
            keySym = None

        # next, try converting Qt key code to a VTK keysym
        if keySym is None:
            try:
                keySym = _keysyms[ev.key()]
            except KeyError:
                keySym = None

        # use "None" as a fallback
        if keySym is None:
            keySym = "None"

        return keyChar, keySym

    def _GetCtrlShift(self, ev):
        ctrl = shift = False

        if hasattr(ev, 'modifiers'):
            if ev.modifiers() & Qt.ShiftModifier:
                shift = True
            if ev.modifiers() & Qt.ControlModifier:
                ctrl = True
        else:
            if self.__saveModifiers & Qt.ShiftModifier:
                shift = True
            if self.__saveModifiers & Qt.ControlModifier:
                ctrl = True

        return ctrl, shift

    @staticmethod
    def _getPixelRatio():
        if PyQtImpl in ["PyQt5", "PySide2", "PySide6"]:
            # Source: https://stackoverflow.com/a/40053864/3388962
            pos = QCursor.pos()
            for screen in QApplication.screens():
                rect = screen.geometry()
                if rect.contains(pos):
                    return screen.devicePixelRatio()
            # Should never happen, but try to find a good fallback.
            return QApplication.instance().devicePixelRatio()
        else:
            # Qt4 seems not to provide any cross-platform means to get the
            # pixel ratio.
            return 1.

    def _setEventInformation(self, x, y, ctrl, shift,
                             key, repeat=0, keysum=None):
        scale = self._getPixelRatio()
        self._Iren.SetEventInformation(int(round(x*scale)),
                                       int(round((self.height()-y-1)*scale)),
                                       ctrl, shift, key, repeat, keysum)

    def enterEvent(self, ev):
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(self.__saveX, self.__saveY,
                                  ctrl, shift, chr(0), 0, None)
        self._Iren.EnterEvent()

    def leaveEvent(self, ev):
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(self.__saveX, self.__saveY,
                                  ctrl, shift, chr(0), 0, None)
        self._Iren.LeaveEvent()

    def mousePressEvent(self, ev):
        ctrl, shift = self._GetCtrlShift(ev)
        repeat = 0
        if ev.type() == QEvent.MouseButtonDblClick:
            repeat = 1
        self._setEventInformation(ev.x(), ev.y(),
                                  ctrl, shift, chr(0), repeat, None)

        self._ActiveButton = ev.button()

        if self._ActiveButton == Qt.LeftButton:
            self._Iren.LeftButtonPressEvent()
        elif self._ActiveButton == Qt.RightButton:
            self._Iren.RightButtonPressEvent()
        elif self._ActiveButton == Qt.MidButton:
            self._Iren.MiddleButtonPressEvent()

    def mouseReleaseEvent(self, ev):
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(ev.x(), ev.y(),
                                  ctrl, shift, chr(0), 0, None)

        if self._ActiveButton == Qt.LeftButton:
            self._Iren.LeftButtonReleaseEvent()
        elif self._ActiveButton == Qt.RightButton:
            self._Iren.RightButtonReleaseEvent()
        elif self._ActiveButton == Qt.MidButton:
            self._Iren.MiddleButtonReleaseEvent()

    def mouseMoveEvent(self, ev):
        self.__saveModifiers = ev.modifiers()
        self.__saveButtons = ev.buttons()
        self.__saveX = ev.x()
        self.__saveY = ev.y()

        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(ev.x(), ev.y(),
                                  ctrl, shift, chr(0), 0, None)
        self._Iren.MouseMoveEvent()

    def keyPressEvent(self, ev):
        key, keySym = self._GetKeyCharAndKeySym(ev)
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(self.__saveX, self.__saveY,
                                  ctrl, shift, key, 0, keySym)
        self._Iren.KeyPressEvent()
        self._Iren.CharEvent()

    def keyReleaseEvent(self, ev):
        key, keySym = self._GetKeyCharAndKeySym(ev)
        ctrl, shift = self._GetCtrlShift(ev)
        self._setEventInformation(self.__saveX, self.__saveY,
                                  ctrl, shift, key, 0, keySym)
        self._Iren.KeyReleaseEvent()

    def wheelEvent(self, ev):
        if hasattr(ev, 'delta'):
            self.__wheelDelta += ev.delta()
        else:
            self.__wheelDelta += ev.angleDelta().y()

        if self.__wheelDelta >= 120:
            self._Iren.MouseWheelForwardEvent()
            self.__wheelDelta = 0
        elif self.__wheelDelta <= -120:
            self._Iren.MouseWheelBackwardEvent()
            self.__wheelDelta = 0

    def GetRenderWindow(self):
        return self._RenderWindow

    def Render(self):
        self.update()


def QVTKRenderWidgetConeExample():
    """A simple example that uses the QVTKRenderWindowInteractor class."""

    from vtkmodules.vtkFiltersSources import vtkConeSource
    from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer
    # load implementations for rendering and interaction factory classes
    import vtkmodules.vtkRenderingOpenGL2
    import vtkmodules.vtkInteractionStyle

    # every QT app needs an app
    app = QApplication.instance()
    if not app:  # pragma: no cover
        app = QApplication(["PyVista"])

    window = QMainWindow()

    # create the widget
    widget = QVTKRenderWindowInteractor(window)
    window.setCentralWidget(widget)
    # if you don't want the 'q' key to exit comment this.
    widget.AddObserver("ExitEvent", lambda o, e, a=app: a.quit())

    ren = vtkRenderer()
    widget.GetRenderWindow().AddRenderer(ren)

    cone = vtkConeSource()
    cone.SetResolution(8)

    coneMapper = vtkPolyDataMapper()
    coneMapper.SetInputConnection(cone.GetOutputPort())

    coneActor = vtkActor()
    coneActor.SetMapper(coneMapper)

    ren.AddActor(coneActor)

    # show the widget
    window.show()

    widget.Initialize()
    widget.Start()

    # start event processing
    # Source: https://doc.qt.io/qtforpython/porting_from2.html
    # 'exec_' is deprecated and will be removed in the future.
    # Use 'exec' instead.
    # try:
    #     app.exec()
    # except AttributeError:
    #     app.exec_()


_keysyms_for_ascii = (
    None, None, None, None, None, None, None, None,
    None, "Tab", None, None, None, None, None, None,
    None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None,
    "space", "exclam", "quotedbl", "numbersign",
    "dollar", "percent", "ampersand", "quoteright",
    "parenleft", "parenright", "asterisk", "plus",
    "comma", "minus", "period", "slash",
    "0", "1", "2", "3", "4", "5", "6", "7",
    "8", "9", "colon", "semicolon", "less", "equal", "greater", "question",
    "at", "A", "B", "C", "D", "E", "F", "G",
    "H", "I", "J", "K", "L", "M", "N", "O",
    "P", "Q", "R", "S", "T", "U", "V", "W",
    "X", "Y", "Z", "bracketleft",
    "backslash", "bracketright", "asciicircum", "underscore",
    "quoteleft", "a", "b", "c", "d", "e", "f", "g",
    "h", "i", "j", "k", "l", "m", "n", "o",
    "p", "q", "r", "s", "t", "u", "v", "w",
    "x", "y", "z", "braceleft", "bar", "braceright", "asciitilde", "Delete",
    )

_keysyms = {
    Qt.Key_Backspace: 'BackSpace',
    Qt.Key_Tab: 'Tab',
    Qt.Key_Backtab: 'Tab',
    # Qt.Key_Clear : 'Clear',
    Qt.Key_Return: 'Return',
    Qt.Key_Enter: 'Return',
    Qt.Key_Shift: 'Shift_L',
    Qt.Key_Control: 'Control_L',
    Qt.Key_Alt: 'Alt_L',
    Qt.Key_Pause: 'Pause',
    Qt.Key_CapsLock: 'Caps_Lock',
    Qt.Key_Escape: 'Escape',
    Qt.Key_Space: 'space',
    # Qt.Key_Prior : 'Prior',
    # Qt.Key_Next : 'Next',
    Qt.Key_End: 'End',
    Qt.Key_Home: 'Home',
    Qt.Key_Left: 'Left',
    Qt.Key_Up: 'Up',
    Qt.Key_Right: 'Right',
    Qt.Key_Down: 'Down',
    Qt.Key_SysReq: 'Snapshot',
    Qt.Key_Insert: 'Insert',
    Qt.Key_Delete: 'Delete',
    Qt.Key_Help: 'Help',
    Qt.Key_0: '0',
    Qt.Key_1: '1',
    Qt.Key_2: '2',
    Qt.Key_3: '3',
    Qt.Key_4: '4',
    Qt.Key_5: '5',
    Qt.Key_6: '6',
    Qt.Key_7: '7',
    Qt.Key_8: '8',
    Qt.Key_9: '9',
    Qt.Key_A: 'a',
    Qt.Key_B: 'b',
    Qt.Key_C: 'c',
    Qt.Key_D: 'd',
    Qt.Key_E: 'e',
    Qt.Key_F: 'f',
    Qt.Key_G: 'g',
    Qt.Key_H: 'h',
    Qt.Key_I: 'i',
    Qt.Key_J: 'j',
    Qt.Key_K: 'k',
    Qt.Key_L: 'l',
    Qt.Key_M: 'm',
    Qt.Key_N: 'n',
    Qt.Key_O: 'o',
    Qt.Key_P: 'p',
    Qt.Key_Q: 'q',
    Qt.Key_R: 'r',
    Qt.Key_S: 's',
    Qt.Key_T: 't',
    Qt.Key_U: 'u',
    Qt.Key_V: 'v',
    Qt.Key_W: 'w',
    Qt.Key_X: 'x',
    Qt.Key_Y: 'y',
    Qt.Key_Z: 'z',
    Qt.Key_Asterisk: 'asterisk',
    Qt.Key_Plus: 'plus',
    Qt.Key_Minus: 'minus',
    Qt.Key_Period: 'period',
    Qt.Key_Slash: 'slash',
    Qt.Key_F1: 'F1',
    Qt.Key_F2: 'F2',
    Qt.Key_F3: 'F3',
    Qt.Key_F4: 'F4',
    Qt.Key_F5: 'F5',
    Qt.Key_F6: 'F6',
    Qt.Key_F7: 'F7',
    Qt.Key_F8: 'F8',
    Qt.Key_F9: 'F9',
    Qt.Key_F10: 'F10',
    Qt.Key_F11: 'F11',
    Qt.Key_F12: 'F12',
    Qt.Key_F13: 'F13',
    Qt.Key_F14: 'F14',
    Qt.Key_F15: 'F15',
    Qt.Key_F16: 'F16',
    Qt.Key_F17: 'F17',
    Qt.Key_F18: 'F18',
    Qt.Key_F19: 'F19',
    Qt.Key_F20: 'F20',
    Qt.Key_F21: 'F21',
    Qt.Key_F22: 'F22',
    Qt.Key_F23: 'F23',
    Qt.Key_F24: 'F24',
    Qt.Key_NumLock: 'Num_Lock',
    Qt.Key_ScrollLock: 'Scroll_Lock',
    }


if __name__ == "__main__":
    print(PyQtImpl)
    QVTKRenderWidgetConeExample()
