# Convenience targets for local development.
#
# Tools are run through `uv run` so they resolve from the project environment
# without requiring the venv to be activated. Override RUN to run directly
# (e.g. `make lint RUN=`) when tools are already on PATH.

PACKAGE ?= pyvistaqt
RUN ?= uv run

all: lint

lint:
	@echo "Running ruff (lint + format check)"
	@$(RUN) ruff check $(PACKAGE)
	@$(RUN) ruff format --check $(PACKAGE)

format:
	@echo "Auto-fixing with ruff"
	@$(RUN) ruff check --fix $(PACKAGE)
	@$(RUN) ruff format $(PACKAGE)

mypy:
	@echo "Running mypy"
	@$(RUN) mypy

coverage:
	@echo "Running coverage"
	@$(RUN) pytest -v --cov $(PACKAGE)

coverage-xml:
	@echo "Reporting XML coverage"
	@$(RUN) pytest -v --cov $(PACKAGE) --cov-report xml

coverage-html:
	@echo "Reporting HTML coverage"
	@$(RUN) pytest -v --cov $(PACKAGE) --cov-report html

.PHONY: all lint format mypy coverage coverage-xml coverage-html
