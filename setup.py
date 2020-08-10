"""
Installation file for python pyvistaqt module
"""
import os
from io import open as io_open

from setuptools import setup

package_name = 'pyvistaqt'

__version__ = None
filepath = os.path.dirname(__file__)
version_file = os.path.join(filepath, package_name, '_version.py')
with io_open(version_file, mode='r') as fd:
    exec(fd.read())

readme_file = os.path.join(filepath, 'README.rst')

setup(
    name=package_name,
    packages=[package_name, package_name],
    version=__version__,
    description='pyvista qt plotter',
    long_description=io_open(readme_file, encoding="utf-8").read(),
    author='PyVista Developers',
    author_email='info@pyvista.org',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],

    url='https://github.com/pyvista/pyvistaqt',
    keywords='vtk numpy plotting mesh qt pyqt',
    python_requires='>=3.5.*',
    install_requires=['pyvista>=0.25.0',
                      'PyQt5>=5.11.3',
                      'imageio>=2.5.0',
    ],
    package_data={'pyvistaqt': [
        os.path.join('data', '*.png'),
    ]}

)
