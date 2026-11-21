"""
Measure the frame rate of the Qt widget and how often VTK renders per frame.

Run it by hand before and after a change to the paint path (``pyvistaqt/rwi.py``
or the render methods in ``pyvistaqt/plotting.py``) and compare the two tables::

    python tools/bench_render.py

Each scene is rotated one degree per frame for a few seconds. Two numbers are
reported per scene:

- VTK renders per frame. This should be 1.0, does not depend on the hardware,
  and is what ``test_render_renders_once`` asserts. 2.0 means a render is
  followed by a paint that renders the same scene again.
- Frames per second. Only compare runs from the same machine and session.

Vertical sync caps the frame rate at the display's refresh rate, which hides
any difference between two versions, so it is turned off unless ``--vsync`` is
given. What it takes depends on the platform:

- NVIDIA on X11 (``QT_QPA_PLATFORM=xcb``): the environment variable
  ``__GL_SYNC_TO_VBLANK=0``, set here before Qt loads the driver. It has no
  effect on Wayland.
- Everywhere else that honors it, native Wayland included: a swap interval of
  0 in the default ``QSurfaceFormat``, installed here before the widget is
  created.

If the frame rates still sit at the refresh rate, vsync is being forced
somewhere else (a driver control panel, the compositor).

On Wayland, a window that the compositor is not presenting (one that opened
behind another window, say) receives no paints at all: the benchmark then only
measures VTK and reports 1.0 renders per frame whatever the code does. Such
rows are marked ``NOT PRESENTED``. A Wayland client cannot raise or move its
window, but it can ask for a particular screen when going full screen, so
``--screen N`` shows the window full screen on screen ``N`` and then returns it
to a normal window there; pick a screen with nothing else on it.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time

SCENES = {
    "1M": ("1M triangles", 700, {}),
    "16M": ("16M triangles", 2800, {}),
    "peel": ("1M translucent + depth peeling", 700, {"opacity": 0.5}),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    parser.add_argument("--vsync", action="store_true", help="leave vertical sync alone (default: turn it off)")
    parser.add_argument("--seconds", type=float, default=3.0, help="how long to time each scene (default: 3)")
    parser.add_argument("--scenes", nargs="+", choices=list(SCENES), default=list(SCENES), help="scenes to run (default: all)")
    parser.add_argument("--size", type=int, nargs=2, default=(1200, 900), metavar=("W", "H"), help="window size (default: 1200 900)")
    parser.add_argument("--screen", type=int, default=None, metavar="N", help="put the window on screen N (see the module docstring)")
    return parser.parse_args()


def main() -> None:  # noqa: C901, PLR0915
    """Run the benchmark."""
    args = _parse_args()
    if not args.vsync:
        # Read by the NVIDIA X11 driver when it is loaded, so before any Qt import.
        os.environ.setdefault("__GL_SYNC_TO_VBLANK", "0")

    import pyvista as pv  # noqa: PLC0415
    from qtpy.QtGui import QSurfaceFormat  # noqa: PLC0415
    from qtpy.QtWidgets import QApplication  # noqa: PLC0415

    import pyvistaqt  # noqa: PLC0415
    from pyvistaqt import BackgroundPlotter  # noqa: PLC0415
    from pyvistaqt.rwi import _default_format  # noqa: PLC0415

    if not args.vsync:
        # pyvistaqt keeps a default format that VTK can use, so start from its own.
        fmt = _default_format()
        fmt.setSwapInterval(0)
        QSurfaceFormat.setDefaultFormat(fmt)
    app = QApplication.instance() or QApplication(sys.argv)

    def spin(sec: float) -> None:
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < sec:
            app.processEvents()
            time.sleep(0.001)

    def to_screen(window, index: int) -> None:  # noqa: ANN001
        window.winId()  # create the native window, which is what takes the screen
        window.windowHandle().setScreen(app.screens()[index])
        for _ in range(5):
            window.showFullScreen()
            spin(1.5)
            window.showNormal()
            spin(1.5)
            if window.windowHandle().isExposed():
                break

    print(f"pyvistaqt {pyvistaqt.__version__} from {Path(pyvistaqt.__file__).parent}")
    print(f"pyvista {pv.__version__} | Qt platform {app.platformName()} | vsync {'left alone' if args.vsync else 'off'}")
    for key in args.scenes:
        label, res, kwargs = SCENES[key]
        p = BackgroundPlotter(show=args.screen is None, auto_update=False, update_app_icon=False, window_size=tuple(args.size))
        p.add_mesh(pv.Sphere(theta_resolution=res, phi_resolution=res), color="tan", **kwargs)
        if kwargs:
            p.enable_depth_peeling(10)
        if args.screen is not None:
            to_screen(p.app_window, args.screen)
        spin(0.5)
        n_render = [0]
        p.renderer.AddObserver("StartEvent", lambda *_, n=n_render: n.__setitem__(0, n[0] + 1))
        n_frame = 0
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < args.seconds:
            p.camera.Azimuth(1)
            p.render()
            app.processEvents()
            app.processEvents()
            n_frame += 1
        elapsed = time.perf_counter() - t0
        # Qt on Wayland withdraws exposure when the compositor stops asking for frames.
        presented = p.app_window.windowHandle().isExposed()
        note = "" if presented else "  NOT PRESENTED: no paints, numbers are not comparable"
        print(f"{label:32s} {n_frame / elapsed:7.1f} frames/s  {n_render[0] / n_frame:.1f} VTK renders per frame{note}")
        p.close()
        spin(0.2)


if __name__ == "__main__":
    main()
