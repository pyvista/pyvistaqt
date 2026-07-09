"""This module contains utilities routines."""  # noqa: D404

from collections.abc import Generator
import contextlib
import os
import sys
from types import ModuleType
from typing import Any
from typing import cast

import pyvista
from qtpy import QtCore
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QMenuBar
import scooby

try:
    import termios
except Exception:  # noqa: BLE001
    termios: ModuleType | None = None  # type: ignore[assignment]  # non-POSIX (e.g. Windows)


def _check_type(var: Any, var_name: str, var_types: list[type[Any]]) -> None:  # noqa: ANN401
    types = tuple(var_types)
    if not isinstance(var, types):
        msg = f"Expected type for ``{var_name}`` is {types!s} but {type(var)} was given."
        raise TypeError(msg)


def _create_menu_bar(parent: Any) -> QMenuBar:  # noqa: ANN401
    """
    Create a menu bar.

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


def _setup_ipython(ipython: Any = None) -> Any:  # noqa: ANN401
    # ipython magic
    if scooby.in_ipython():  # pragma: no cover
        from IPython import get_ipython  # noqa: PLC0415

        ipython = get_ipython()
        ipython.run_line_magic("gui", "qt")

        from IPython.external.qt_for_kernel import QtGui  # noqa: PLC0415

        QtGui.QApplication.instance()
    return ipython


@contextlib.contextmanager
def _prefer_xcb_on_wayland() -> Generator[None, None, None]:
    """
    Temporarily prefer the XWayland (``xcb``) Qt platform plugin on Wayland.

    VTK's Linux render window is X11-based (``vtkXOpenGLRenderWindow``) and
    cannot embed into a native Wayland surface, so a native-Wayland
    ``QApplication`` makes :class:`~pyvistaqt.QtInteractor` abort with a fatal,
    uncatchable ``X Error ... BadWindow`` as soon as it is realized (see
    `issue #445 <https://github.com/pyvista/pyvistaqt/issues/445>`_).

    When ``pyvistaqt`` is the one creating the ``QApplication`` and the user has
    not pinned ``QT_QPA_PLATFORM``, set ``QT_QPA_PLATFORM=xcb`` for the duration
    of this context if a Wayland session with XWayland is detected, then restore
    ``os.environ`` to its previous state. Qt only reads the variable while the
    ``QApplication`` is constructed, so wrap that call; setting
    ``QT_QPA_PLATFORM`` yourself (e.g. to ``wayland``) opts out.
    """
    should_prefer = (
        QApplication.instance() is None  # too late once the plugin is chosen
        and not os.environ.get("QT_QPA_PLATFORM")  # respect an explicit choice
        and bool(os.environ.get("WAYLAND_DISPLAY"))  # a Wayland session
        and bool(os.environ.get("DISPLAY"))  # with XWayland to fall back to
    )
    if not should_prefer:
        yield
        return
    original = os.environ.get("QT_QPA_PLATFORM")
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("QT_QPA_PLATFORM", None)
        else:  # an empty-string override was set: put it back verbatim
            os.environ["QT_QPA_PLATFORM"] = original


def _setup_application(app: QApplication | None = None) -> QApplication:
    # run within python
    if app is None:
        # QApplication.instance() is typed as returning the QCoreApplication
        # base class, but for a Qt widgets app it is a QApplication.
        app = cast("QApplication | None", QApplication.instance())
        if not app:  # pragma: no cover
            with _prefer_xcb_on_wayland():
                app = QApplication(["PyVista"])
    return app


def _check_wayland(off_screen: bool) -> None:  # noqa: FBT001
    """
    Fail early with guidance on an unsupported native-Wayland platform plugin.

    If we reach on-screen setup with a native Wayland ``QApplication`` already
    created (so :func:`_prefer_xcb_on_wayland` could not intervene), VTK's X11
    render window will abort the process with ``X Error ... BadWindow``. Raise a
    clear, catchable error instead (see `issue #445
    <https://github.com/pyvista/pyvistaqt/issues/445>`_).
    """
    if off_screen:  # no window is embedded, so no X11/Wayland surface clash
        return
    # QApplication.instance() is typed as the QCoreApplication base class, which
    # has no platformName(); for a widgets app it is really a QApplication.
    app = cast("QApplication | None", QApplication.instance())
    if app is None:  # pragma: no cover
        return
    platform_name = app.platformName()
    if not platform_name.startswith("wayland"):
        return
    msg = (
        "pyvistaqt cannot render on-screen with the native Wayland Qt platform "
        f"plugin (QApplication.platformName()={platform_name!r}): VTK embeds "
        "via an X11 render window, which aborts with 'X Error ... BadWindow' on "
        "a Wayland surface (https://github.com/pyvista/pyvistaqt/issues/445). "
        "Set the environment variable QT_QPA_PLATFORM=xcb *before* the "
        "QApplication is created to use XWayland, e.g. at the top of your "
        "script:\n"
        "    import os\n"
        "    os.environ['QT_QPA_PLATFORM'] = 'xcb'"
    )
    raise RuntimeError(msg)


def _setup_off_screen(off_screen: bool | None = None) -> bool:  # noqa: FBT001
    if off_screen is None:
        off_screen = pyvista.OFF_SCREEN
    return off_screen


# Strong references to the installed guards, keyed by their application, so
# that the connected slots are not garbage collected and each application is
# only wired up once.
_TERMINAL_OUTPUT_GUARDS: list[tuple[QApplication, "_TerminalOpostGuard"]] = []


class _TerminalOpostGuard:
    """
    Force terminal output post-processing on while Qt processes events.

    See :func:`_setup_terminal_output_fix` for why this is needed. ``enable``
    is connected to the event dispatcher's ``awake`` signal and ``restore`` to
    ``aboutToBlock``, so the terminal is only touched while it is in raw mode
    and is always handed back to the REPL in its original state.
    """

    def __init__(self, fd: int) -> None:

        self._fd = fd
        self._saved: list[Any] | None = None

    def enable(self) -> None:
        """Restore ``OPOST``/``ONLCR`` if the terminal is in raw mode."""
        assert termios is not None  # noqa:S101
        try:
            attrs = termios.tcgetattr(self._fd)
        except termios.error:  # pragma: no cover
            return
        if attrs[1] & termios.OPOST:  # already sane, nothing to do
            return
        new = list(attrs)
        new[1] = attrs[1] | termios.OPOST | termios.ONLCR
        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, new)
        except termios.error:  # pragma: no cover
            return
        self._saved = attrs

    def restore(self) -> None:
        """Put the terminal back the way the REPL left it."""
        if self._saved is None:
            return
        assert termios is not None  # noqa:S101
        with contextlib.suppress(termios.error):
            termios.tcsetattr(self._fd, termios.TCSANOW, self._saved)
        self._saved = None


def _terminal_output_fd() -> int | None:
    """Return the fd of the controlling terminal, or None if not a TTY/POSIX."""
    if termios is None:  # pragma: no cover  # non-POSIX (e.g. Windows)
        return None
    for stream in (sys.stderr, sys.stdout):
        try:
            fd = stream.fileno()
            termios.tcgetattr(fd)
        except (OSError, ValueError, termios.error):
            continue
        return fd
    return None


def _setup_terminal_output_fix(app: QApplication) -> None:
    """
    Keep terminal output readable while Qt processes events.

    Python 3.13's new interactive REPL (``pyrepl``) reads input with terminal
    output post-processing (``OPOST``) disabled, and processes Qt events via
    ``PyOS_InputHook`` while still in that raw state. Any text written to the
    terminal during event processing -- for example a traceback surfaced by
    ``pyvista``'s ``try_callback`` from an event callback -- then lacks
    carriage returns and "staircases" down the screen. Restore
    ``OPOST``/``ONLCR`` while Qt is processing events, and hand the terminal
    back to the REPL unchanged afterwards.

    This is a no-op unless we are in an interactive session attached to a
    terminal on a POSIX platform, and even then only takes effect while the
    terminal is actually in raw mode.
    """
    # Only meaningful for an interactive session attached to a terminal.
    if not hasattr(sys, "ps1") and not sys.flags.interactive:
        return
    if any(existing is app for existing, _ in _TERMINAL_OUTPUT_GUARDS):
        return  # already installed for this application
    fd = _terminal_output_fd()
    if fd is None:
        return
    dispatcher = QtCore.QAbstractEventDispatcher.instance()
    if dispatcher is None:
        return
    guard = _TerminalOpostGuard(fd)
    dispatcher.awake.connect(guard.enable)
    dispatcher.aboutToBlock.connect(guard.restore)
    _TERMINAL_OUTPUT_GUARDS.append((app, guard))
