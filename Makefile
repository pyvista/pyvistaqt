# Convenience targets for local development.

PACKAGE ?= pyvistaqt

all: lint

lint:
	@echo "Running ruff (lint + format check)"
	@ruff check $(PACKAGE)
	@ruff format --check $(PACKAGE)

format:
	@echo "Auto-fixing with ruff"
	@ruff check --fix $(PACKAGE)
	@ruff format $(PACKAGE)

mypy:
	@echo "Running mypy"
	@mypy

coverage:
	@echo "Running coverage"
	@pytest -v --cov $(PACKAGE)

coverage-xml:
	@echo "Reporting XML coverage"
	@pytest -v --cov $(PACKAGE) --cov-report xml

coverage-html:
	@echo "Reporting HTML coverage"
	@pytest -v --cov $(PACKAGE) --cov-report html

.PHONY: all lint format mypy coverage coverage-xml coverage-html
