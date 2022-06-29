# Simple makefile to simplify repetitive build env management tasks under posix

BLACK_DIRS ?= ./pyvistaqt/
ISORT_DIRS ?= ./pyvistaqt/
PYCODESTYLE_DIRS ?= ./pyvistaqt/
PYLINT_DIRS ?= ./pyvistaqt/
MYPY_DIRS ?= "mypy_checklist.txt"
FLAKE8_DIRS ?= ./pyvistaqt/
CODESPELL_DIRS ?= ./
PYDOCSTYLE_DIRS ?= ./pyvistaqt/
COVERAGE_DIRS ?= ./pyvistaqt/
COVERAGE_HTML_DIRS ?= ./pyvistaqt/
COVERAGE_XML_DIRS ?= ./pyvistaqt/

EXTRA_CODESPELL_OPTIONS ?= --config .codespellrc
EXTRA_BLACK_OPTIONS ?= --config pyproject.toml
EXTRA_ISORT_OPTIONS ?= --check --settings=.isort.cfg
EXTRA_PYLINT_OPTIONS ?= -rn -sn --rcfile=.pylintrc
EXTRA_PYCODESTYLE_OPTIONS ?= --config=.pycodestyle
EXTRA_MYPY_OPTIONS ?= --config-file mypy.ini
EXTRA_FLAKE8_OPTIONS ?= --config=.flake8
EXTRA_PYDOCSTYLE_OPTIONS = --config=pyproject.toml

all: srcstyle doctest

srcstyle: black isort pylint pycodestyle mypy flake8

doctest: codespell pydocstyle

black:
	@echo "Running black"
	@black $(BLACK_DIRS) $(EXTRA_BLACK_OPTIONS)

isort:
	@echo "Running isort"
	@isort $(ISORT_DIRS) $(EXTRA_ISORT_OPTIONS)

pylint:
	@echo "Running pylint"
	@pylint $(PYLINT_DIRS) $(EXTRA_PYLINT_OPTIONS)

pycodestyle:
	@echo "Running pycodestyle"
	@pycodestyle $(PYCODESTYLE_DIRS) $(EXTRA_PYCODESTYLE_OPTIONS)

mypy:
	@echo "Running mypy"
	@mypy @$(MYPY_DIRS) $(EXTRA_MYPY_OPTIONS)

flake8:
	@echo "Running flake8"
	@flake8 $(FLAKE8_DIRS) $(EXTRA_FLAKE8_OPTIONS)

codespell:
	@echo "Running codespell"
	@codespell $(CODESPELL_DIRS) $(EXTRA_CODESPELL_OPTIONS)

pydocstyle:
	@echo "Running pydocstyle"
	@pydocstyle $(PYDOCSTYLE_DIRS) $(EXTRA_PYDOCSTYLE_OPTIONS)

coverage:
	@echo "Running coverage"
	@pytest -v --cov $(COVERAGE_DIRS)

coverage-xml:
	@echo "Reporting XML coverage"
	@pytest -v --cov $(COVERAGE_XML_DIRS) --cov-report xml

coverage-html:
	@echo "Reporting HTML coverage"
	@pytest -v --cov $(COVERAGE_HTML_DIRS) --cov-report html
