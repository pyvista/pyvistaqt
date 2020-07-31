# Simple makefile to simplify repetitive build env management tasks under posix

BLACK_DIRS ?= ./pyvistaqt/
ISORT_DIRS ?= ./pyvistaqt/
PYCODESTYLE_DIRS ?= ./pyvistaqt/
FLAKE8_DIRS ?= ./pyvistaqt/
CODESPELL_DIRS ?= ./
CODESPELL_SKIP ?= "*.pyc,*.txt,*.gif,*.png,*.jpg,*.ply,*.vtk,*.vti,*.js,*.html,*.doctree,*.ttf,*.woff,*.woff2,*.eot,*.mp4,*.inv,*.pickle,*.ipynb,flycheck*,./.git/*,./.hypothesis/*,*.yml,./docs/_build/*,./docs/images/*,./dist/*,./.ci/*"
CODESPELL_IGNORE ?= "ignore_words.txt"
EXTRA_PYCODESTYLE_OPTIONS ?= --ignore="E501,E203"
EXTRA_FLAKE8_OPTIONS ?= --ignore="E501,E203"

all: doctest

doctest: codespell pydocstyle

black:
	@echo "Running black"
	@black $(BLACK_DIRS)

isort:
	@echo "Running isort"
	@isort $(ISORT_DIRS)

pycodestyle:
	@echo "Running pycodestyle"
	@pycodestyle $(PYCODESTYLE_DIRS) $(EXTRA_PYCODESTYLE_OPTIONS)

flake8:
	@echo "Running flake8"
	@pycodestyle $(FLAKE8_DIRS) $(EXTRA_FLAKE8_OPTIONS)

codespell:
	@echo "Running codespell"
	@codespell $(CODESPELL_DIRS) -S $(CODESPELL_SKIP) -I $(CODESPELL_IGNORE)

pydocstyle:
	@echo "Running pydocstyle"
	@pydocstyle pyvista

coverage:
	@echo "Running coverage"
	@pytest -v --cov pyvistaqt

coverage-xml:
	@echo "Reporting XML coverage"
	@pytest -v --cov pyvistaqt --cov-report xml

coverage-html:
	@echo "Reporting HTML coverage"
	@pytest -v --cov pyvistaqt --cov-report html
