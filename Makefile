.PHONY: install format lint typecheck test build smoke-wheel check

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ".[dev]"

format:
	$(PYTHON) -m black src tests

lint:
	$(PYTHON) -m ruff check src tests

typecheck:
	$(PYTHON) -m mypy src

test:
	$(PYTHON) -m pytest

build:
	rm -rf build dist
	$(PYTHON) -m build

smoke-wheel: build
	bash scripts/smoke_wheel.sh dist/*.whl

check: lint typecheck test smoke-wheel
