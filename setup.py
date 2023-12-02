"""
Installation file for python pyvistaqt module
"""
import os
from pathlib import Path
from io import open as io_open

from setuptools import setup

package_name = 'pyvistaqt'
readme_file = Path(__file__).parent / 'README.rst'

setup(
    name=package_name,
    packages=[package_name, package_name],
    description='pyvista qt plotter',
    long_description=readme_file.read_text(),
    long_description_content_type='text/x-rst',
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    url='https://github.com/pyvista/pyvistaqt',
    keywords='vtk numpy plotting mesh qt',
    python_requires='>=3.7',
    setup_requires=["setuptools>=45", "setuptools_scm>=6.2"],
    use_scm_version={
        "write_to": "pyvistaqt/_version.py",
        "version_scheme": "release-branch-semver",
    },
    install_requires=[
        'pyvista>=0.32.0',
        'QtPy>=1.9.0',
    ],
    package_data={'pyvistaqt': [
        os.path.join('data', '*.png'),
    ]}

)
