#########
PyVistaQt
#########


.. image:: https://img.shields.io/pypi/v/pyvistaqt
   :target: https://pypi.org/project/pyvistaqt/
   :alt: PyPI

.. image:: https://img.shields.io/conda/vn/conda-forge/pyvistaqt
   :target: https://anaconda.org/conda-forge/pyvistaqt
   :alt: conda-forge

.. image:: https://dev.azure.com/pyvista/PyVista/_apis/build/status/pyvista.pyvistaqt?branchName=master
   :target: https://dev.azure.com/pyvista/PyVista/_build/latest?definitionId=9&branchName=master
   :alt: Azure Pipelines

.. image:: https://github.com/pyvista/pyvistaqt/actions/workflows/ci.yml/badge.svg?branch=master
   :target: https://github.com/pyvista/pyvistaqt/actions?query=branch:master+event:push
   :alt: GitHub Actions

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: MIT License

.. image:: https://codecov.io/gh/pyvista/pyvistaqt/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/pyvista/pyvistaqt
  :alt: Codecov

.. image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat
  :target: https://timothycrosley.github.io/isort
  :alt: isort

.. image:: https://img.shields.io/badge/%20linter-pylint-%231674b1?style=flat
  :target: https://github.com/PyCQA/pylint
  :alt: pylint

.. image:: https://img.shields.io/badge/%20type_checker-mypy-%231674b1?style=flat
  :target: https://github.com/python/mypy
  :alt: mypy

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=flat
  :target: https://github.com/psf/black
  :alt: black

``pyvistaqt`` is a helper module for ``pyvista`` to enable you to
plot using ``pyqt`` by placing a vtk-widget into a background render.
This can be quite useful when you desire to update your plot in
real-time.

Documentation
=============

For the installation and usage of this package, please visit the
`PyVistaQt documentation <http://qtdocs.pyvista.org/>`_.

Refer to the `PyVista documentation <http://docs.pyvista.org/>`_ for detailed
installation and usage details of the core package which is used
alongside this package.

For general questions about the project, its applications, or about software
usage, please create an issue in the `pyvista/pyvista-support`_ repository
where the community can collectively address your questions. You are also
welcome to join us on Slack_ or send one of the developers an email.
The project support team can be reached at `info@pyvista.org`_.

.. _pyvista/pyvista-support: https://github.com/pyvista/pyvista-support
.. _Slack: http://slack.pyvista.org
.. _info@pyvista.org: mailto:info@pyvista.org


Installation
============

Installation using ``pip`` is::

    $ pip install pyvistaqt


To install this package with ``conda`` run::

    $ conda install -c conda-forge pyvistaqt


You can also visit `PyPI <https://pypi.org/project/pyvistaqt/>`_ or
`GitHub <https://github.com/pyvista/pyvistaqt>`_ to download the source.

Once installed, use the ``pyvistaqt.BackgroundPlotter`` like any PyVista
plotter.


Contributing
============

We absolutely welcome contributions. ``pyvistaqt`` is maintained on a
volunteer basis and thus we need to foster a community that can
support user questions and develop new features to make this software
a useful tool for all users while encouraging every member of the
community to share their ideas. To learn more about contributing to
PyVista, please see the the ``pyvista`` `Contributing Guide`_ and
`Code of Conduct`_.

.. _Contributing Guide: https://github.com/pyvista/pyvista/blob/master/CONTRIBUTING.md
.. _Code of Conduct: https://github.com/pyvista/pyvista/blob/master/CODE_OF_CONDUCT.md

License
=======
While ``pyvistaqt`` is under the MIT license, ``pyqt5`` is subject to
the GPL license.  Please see deails at
`Riverbank License FAQ <https://www.riverbankcomputing.com/commercial/license-faq>`_.
