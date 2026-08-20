"""
Fail unless Qt actually connected to the Wayland compositor.

``QT_QPA_PLATFORM=wayland`` is a request, not a guarantee: a missing plugin,
a missing socket, or a ``wayland;xcb`` style fallback list all end with Qt
happily running on something else. A Wayland job that silently ran on xcb
would report success while testing nothing, so assert the live platform name
before any test runs.
"""

from __future__ import annotations

import os
import sys

from qtpy.QtGui import QGuiApplication
from qtpy.QtGui import QOpenGLContext

EXPECTED = "wayland"


def main() -> int:
    """Report the platform Qt chose and fail if it is not Wayland."""
    for var in ("QT_QPA_PLATFORM", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"):
        print(f"{var}={os.environ.get(var, '<unset>')}")

    app = QGuiApplication([])
    name = app.platformName()
    print(f"QGuiApplication.platformName() = {name!r}")
    screens = app.screens()
    for screen in screens:
        size = screen.size()
        print(f"screen {screen.name()!r}: {size.width()}x{size.height()}")

    if name != EXPECTED:
        print(f"ERROR: expected {EXPECTED!r}, got {name!r}", file=sys.stderr)
        return 1
    if not screens:
        print("ERROR: compositor exposed no screen", file=sys.stderr)
        return 1

    # A compositor running the pixman renderer advertises neither wl_drm nor
    # linux-dmabuf, so Mesa hands out no EGL context and QOpenGLWidget has
    # nothing to draw into. That surfaces far from its cause once the tests
    # start, so check it here where the fix (weston --renderer=gl) is obvious.
    context = QOpenGLContext()
    if not context.create():
        print("ERROR: no GL context on this compositor", file=sys.stderr)
        return 1
    fmt = context.format()
    print(f"GL context: version {fmt.majorVersion()}.{fmt.minorVersion()}, samples={fmt.samples()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
