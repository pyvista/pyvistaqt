.. title:: pyvistaqt


Overview
********

.. image:: https://img.shields.io/pypi/v/pyvistaqt
   :target: https://pypi.org/project/pyvistaqt/
   :alt: PyPI

.. image:: https://img.shields.io/conda/vn/conda-forge/pyvistaqt
   :target: https://anaconda.org/conda-forge/pyvistaqt
   :alt: conda-forge

.. image:: https://dev.azure.com/pyvista/PyVista/_apis/build/status/pyvista.pyvistaqt?branchName=master
   :target: https://dev.azure.com/pyvista/PyVista/_build/latest?definitionId=9&branchName=master
   :alt: Azure Pipelines

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: MIT License

The python package ``pyvistaqt`` extends the
functionality of ``pyvista`` through the usage of *Qt*. 
Since *Qt* applications operates in a separate thread than VTK,
you can simultaneously have an active VTK plot and a non-blocking Python session.

.. figure:: ./images/user-generated/qt_multiplot.png
    :width: 450pt

    pyvistaqt BackgroundPlotter


.. toctree::
   :hidden:

   self


Getting Started
***************

Installation using ``pip`` is::

    $ pip install pyvistaqt


To install this package with ``conda`` run::

    $ conda install -c conda-forge pyvistaqt


You can also visit `PyPI <https://pypi.org/project/pyvistaqt/>`_ or
`GitHub <https://github.com/pyvista/pyvistaqt>`_ to download the source.

Once installed, use the :class:`pyvistaqt.BackgroundPlotter` like any PyVista
plotter.


Brief Example
~~~~~~~~~~~~~

Create an instance of the :class:`pyvistaqt.BackgroundPlotter` and plot a
sphere.

.. code:: python

    import pyvista as pv
    from pyvistaqt import BackgroundPlotter

    sphere = pv.Sphere()

    plotter = BackgroundPlotter()
    plotter.add_mesh(sphere)


.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :hidden:

   usage
   api_reference


License
*******

``pyvistaqt`` is under the MIT license.
However, Qt bindings have licenses of their own.

Historically, ``pyvistaqt`` has used ``pyqt5``, which is subject
to the GPL license. See details at
`Riverbank License FAQ <https://www.riverbankcomputing.com/commercial/license-faq>`_.

``pyvistaqt`` is transitioning to using ``qtpy``

> QtPy is a small abstraction layer that lets you write applications using a single API call to either PyQt or PySide.

Please refer to the `QtPy documentation <https://github.com/spyder-ide/qtpy>`_
to learn more.