.PHONY: setup lint format test check clean

PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

setup:  ## Create venv, install dev deps, install git hooks
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"
	$(BIN)/pre-commit install

lint:  ## Lint and check formatting (same as CI)
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

format:  ## Auto-fix lint issues and format
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

test:  ## Run unit tests with coverage
	$(BIN)/pytest --cov --cov-report=term-missing

check: lint test  ## Everything CI runs

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache .coverage coverage.xml report.xml build dist *.egg-info src/*.egg-info
