# Simple makefile to simplify repetitive build env management tasks under posix

PYCODESTYLE_DIRS ?= ./pyvistaqt/
PYLINT_DIRS ?= ./pyvistaqt/
COVERAGE_DIRS ?= ./pyvistaqt/
COVERAGE_HTML_DIRS ?= ./pyvistaqt/
COVERAGE_XML_DIRS ?= ./pyvistaqt/

EXTRA_PYLINT_OPTIONS ?= -rn -sn --rcfile=.pylintrc
EXTRA_PYCODESTYLE_OPTIONS ?= --config=.pycodestyle

all: srcstyle

srcstyle: pylint pycodestyle

pylint:
	@echo "Running pylint"
	@pylint $(PYLINT_DIRS) $(EXTRA_PYLINT_OPTIONS)

pycodestyle:
	@echo "Running pycodestyle"
	@pycodestyle $(PYCODESTYLE_DIRS) $(EXTRA_PYCODESTYLE_OPTIONS)

coverage:
	@echo "Running coverage"
	@pytest -v --cov $(COVERAGE_DIRS)

coverage-xml:
	@echo "Reporting XML coverage"
	@pytest -v --cov $(COVERAGE_XML_DIRS) --cov-report xml

coverage-html:
	@echo "Reporting HTML coverage"
	@pytest -v --cov $(COVERAGE_HTML_DIRS) --cov-report html
