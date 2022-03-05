# Simple makefile to simplify repetitive build env management tasks under posix

BLACK_DIRS ?= ./pyvistaqt/
ISORT_DIRS ?= ./pyvistaqt/*.py
PYCODESTYLE_DIRS ?= ./pyvistaqt/
PYLINT_DIRS ?= ./pyvistaqt/
MYPY_DIRS ?= "mypy_checklist.txt"
FLAKE8_DIRS ?= ./pyvistaqt/
CODESPELL_DIRS ?= ./
CODESPELL_SKIP ?= "*.json,*.pyc,*.txt,*.gif,*.png,*.jpg,*.ply,*.vtk,*.vti,*.js,*.html,*.doctree,*.ttf,*.woff,*.woff2,*.eot,*.mp4,*.inv,*.pickle,*.ipynb,flycheck*,./.git/*,./.hypothesis/*,*.yml,./docs/_build/*,./docs/images/*,./dist/*,./.ci/*"
CODESPELL_IGNORE ?= "ignore_words.txt"
EXTRA_PYCODESTYLE_OPTIONS ?= --ignore="E501,E203,W503"
EXTRA_FLAKE8_OPTIONS ?= --ignore="E501,E203,W503"

all: srcstyle doctest

srcstyle: black isort pylint pycodestyle mypy flake8

doctest: codespell pydocstyle

black:
	@echo "Running black"
	@black --check $(BLACK_DIRS)

isort:
	@echo "Running isort"
	@isort --check $(ISORT_DIRS)

pylint:
	@echo "Running pylint"
	@pylint $(PYLINT_DIRS) --rcfile=.pylintrc

pycodestyle:
	@echo "Running pycodestyle"
	@pycodestyle $(PYCODESTYLE_DIRS) $(EXTRA_PYCODESTYLE_OPTIONS)

mypy:
	@echo "Running mypy"
	@mypy @$(MYPY_DIRS)

flake8:
	@echo "Running flake8"
	@flake8 $(FLAKE8_DIRS) $(EXTRA_FLAKE8_OPTIONS)

codespell:
	@echo "Running codespell"
	@codespell $(CODESPELL_DIRS) -S $(CODESPELL_SKIP) -I $(CODESPELL_IGNORE)

pydocstyle:
	@echo "Running pydocstyle"
	@pydocstyle pyvistaqt

coverage:
	@echo "Running coverage"
	@pytest -v --cov pyvistaqt

coverage-xml:
	@echo "Reporting XML coverage"
	@pytest -v --cov pyvistaqt --cov-report xml

coverage-html:
	@echo "Reporting HTML coverage"
	@pytest -v --cov pyvistaqt --cov-report html
