from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkRenderingCore import (vtkActor, vtkPolyDataMapper,
                                         vtkRenderer)

from qtpy.QtWidgets import QMainWindow
from pyvistaqt.rwi import QVTKRenderWindowInteractor


def test_rwi(qapp):
    window = QMainWindow()

    # create the widget
    widget = QVTKRenderWindowInteractor(window)
    window.setCentralWidget(widget)

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
