"""Tests for resolving VTK through the backend selected by PyVista."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
import sys
from types import ModuleType

import pytest

from pyvistaqt import _vtk

ROOT = Path(__file__).parent.parent
ROOTS = [ROOT / "pyvistaqt", Path(__file__).parent]
VTK_CLASSES = [
    "vtkActor",
    "vtkGenericOpenGLRenderWindow",
    "vtkGenericRenderWindowInteractor",
    "vtkObjectBase",
    "vtkRenderer",
]


def _direct_vtk_imports(root: Path) -> list[str]:
    """Return direct VTK imports outside the backend resolver."""
    found = []
    for path in sorted(root.rglob("*.py")):
        if path.name == "_vtk.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                modules = [(node.module or "").split(".")[0]]
            elif isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            else:
                continue
            if {"vtk", "vtkmodules"}.intersection(modules):
                found.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    return found


@pytest.mark.parametrize("root", ROOTS, ids=["package", "tests"])
def test_no_direct_vtk_imports(root: Path) -> None:
    """Prevent stock VTK from being loaded alongside another backend."""
    assert not (found := _direct_vtk_imports(root)), "import through pyvistaqt._vtk instead:\n  " + "\n  ".join(found)


@pytest.mark.parametrize("name", VTK_CLASSES)
def test_vtk_class_resolves(name: str) -> None:
    """Resolve every VTK class used by pyvistaqt."""
    assert callable(getattr(_vtk, name))


def test_backend_matches_pyvista() -> None:
    """Use PyVista's backend selection, including legacy defaults."""
    try:
        pyvista_vtk = importlib.import_module("pyvista._vtk")
    except ModuleNotFoundError:
        pyvista_vtk = importlib.import_module("pyvista.plotting._vtk")

    assert getattr(pyvista_vtk, "_VTK_ROOT", "vtkmodules") == _vtk.VTK_BACKEND
    assert getattr(pyvista_vtk, "_VTK_ROOT_IS_FLAT", False) == _vtk.BACKEND_IS_FLAT


def test_unknown_class_has_actionable_error() -> None:
    """Explain how to add a class missing from PyVista's exports."""
    with pytest.raises(AttributeError, match="VTK backend"):
        _ = _vtk.vtkNotARealClass


def test_flat_backend_resolves_from_root(monkeypatch) -> None:
    """Resolve classes from a backend with a flat namespace."""
    backend = ModuleType("flat_vtk")
    backend.vtkTestClass = expected = object()
    monkeypatch.setitem(sys.modules, backend.__name__, backend)
    monkeypatch.setattr(_vtk, "_pyvista_vtk", ModuleType("pyvista_vtk"))
    monkeypatch.setattr(_vtk, "VTK_BACKEND", backend.__name__)
    monkeypatch.setattr(_vtk, "BACKEND_IS_FLAT", True)

    assert _vtk.__getattr__("vtkTestClass") is expected


def test_flat_backend_can_fall_back_to_submodule(monkeypatch) -> None:
    """Allow a flat backend to keep exceptional classes in submodules."""
    backend = ModuleType("flat_vtk")
    module = ModuleType("flat_vtk.vtkCommonCore")
    module.vtkObjectBase = expected = object()
    monkeypatch.setitem(sys.modules, backend.__name__, backend)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(_vtk, "_pyvista_vtk", ModuleType("pyvista_vtk"))
    monkeypatch.setattr(_vtk, "VTK_BACKEND", backend.__name__)
    monkeypatch.setattr(_vtk, "BACKEND_IS_FLAT", True)

    assert _vtk.__getattr__("vtkObjectBase") is expected


def test_render_window_uses_pyvista_backend() -> None:
    """Build the render window from the backend selected by PyVista."""
    render_window = _vtk.vtkGenericOpenGLRenderWindow()
    assert type(render_window).__module__.startswith(_vtk.VTK_BACKEND)
