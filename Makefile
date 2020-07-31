# Simple makefile to simplify repetitive build env management tasks under posix

SRC_DIR = ./pyvistaqt
BLACK_DIRS ?= $(SRC_DIR)
PYLINT_DIRS ?= $(SRC_DIR)
CODESPELL_DIRS ?= $(SRC_DIR) ./tests
CODESPELL_SKIP ?= "*.pyc,*.txt,*.gif,*.png,*.jpg,*.ply,*.vtk,*.vti,*.js,*.html,*.doctree,*.ttf,*.woff,*.woff2,*.eot,*.mp4,*.inv,*.pickle,*.ipynb,flycheck*,./.git/*,./.hypothesis/*,*.yml,./docs/_build/*,./docs/images/*,./dist/*,./.ci/*"
CODESPELL_IGNORE ?= "ignore_words.txt"

all: doctest

doctest: codespell pydocstyle

black:
	@echo "Running black"
	@black $(BLACK_DIRS)

isort:
	@echo "Running isort"
	@isort $(ISORT_DIRS)

pylint:
	@echo "Running pylint"
	@pylint $(PYLINT_DIRS)

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
