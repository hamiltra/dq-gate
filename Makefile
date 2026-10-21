.PHONY: setup lint format test check data load-raw dbt-image clean

PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

setup:  ## Create venv, install dev deps, install git hooks
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev,snowflake]"
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

data:  ## Generate synthetic CSVs into data/synthetic (add ARGS=--inject-defects for the demo data)
	$(BIN)/python scripts/generate_data.py $(ARGS)

load-raw: data  ## Generate and load the synthetic data into Snowflake RAW
	$(BIN)/python scripts/load_raw.py

dbt-image:  ## Build the pinned dbt Docker image
	docker build -t dq-gate-dbt -f dbt/Dockerfile .

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache .coverage coverage.xml report.xml build dist *.egg-info src/*.egg-info
