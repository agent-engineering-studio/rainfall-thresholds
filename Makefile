.PHONY: check lint format typecheck test bench build figures docs

check: lint typecheck test bench

lint:
	uv run ruff check
	uv run ruff format --check

format:
	uv run ruff format
	uv run ruff check --fix

typecheck:
	uv run mypy

test:
	uv run pytest --cov --cov-report=term-missing

bench:
	uv run python -m benchmarks.run --check

build:
	uv build

figures:
	uv run --with matplotlib python docs/make_figures.py

docs:
	uv run --group docs zensical build --strict
