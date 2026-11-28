.PHONY: help check lint format typecheck test bench build figures docs notebooks demo \
        docker down docker-build docker-up docker-down docker-bench docker-python \
        mcp app app-test app-up

# Containers. Every name starts with NAME (rainfall-thresholds-ui, -mcp,
# -notebooks), and the ports clash with no sister library. A second copy:
#   make docker NAME=rt-dev TARATURA_PORT=3101 RAINFALL_THRESHOLDS_MCP_PORT=8785 RAINFALL_THRESHOLDS_PORT=8891
NAME ?= $(or $(RAINFALL_THRESHOLDS_NAME),rainfall-thresholds)
TARATURA_PORT ?= 3001
RAINFALL_THRESHOLDS_MCP_PORT ?= 8775
RAINFALL_THRESHOLDS_PORT ?= 8881
export RAINFALL_THRESHOLDS_NAME := $(NAME)
export TARATURA_PORT RAINFALL_THRESHOLDS_MCP_PORT RAINFALL_THRESHOLDS_PORT

help:  ## List the commands
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' | expand -t 16

# Development

check: lint typecheck test bench  ## ruff + mypy --strict + pytest + the benchmarks, the CI gate

lint:  ## ruff check and format check
	uv run ruff check
	uv run ruff format --check

format:  ## Format the code and fix what ruff can
	uv run ruff format
	uv run ruff check --fix

typecheck:  ## mypy --strict
	uv run mypy

test:  ## The tests, offline
	uv run pytest --cov --cov-report=term-missing

bench:  ## The known cases and the faithfulness set (as in CI)
	uv run python -m benchmarks.run --check
	uv run python -m benchmarks.faithful --check

build:  ## The wheel and the sdist
	uv build

figures:  ## The figures of the README
	uv run --with matplotlib python docs/make_figures.py

docs:  ## The documentation site, llms.txt and the skill
	uv run --group docs zensical build --strict
	uv run --group docs python tools/build_llms.py

notebooks:  ## Run every notebook again and save the results (04 needs the network)
	cd notebooks && uv run --group examples jupyter nbconvert --to notebook --execute --inplace *.ipynb

mcp:  ## The MCP server over HTTP, here: http://127.0.0.1:8775/mcp
	uv run --extra mcp rainfall-thresholds-mcp --transport streamable-http --port $(RAINFALL_THRESHOLDS_MCP_PORT)

# The calibration bench (app/), the page for a public body.

demo: app  ## The calibration bench, here: http://127.0.0.1:8000 (needs uv and npm)

app:
	sh app/vendor.sh
	cd app && uv run uvicorn taratura.api:app --reload

app-test:  ## The tests of the calibration bench
	cd app && uv run pytest

# Docker. Every target goes through `docker compose`, never `docker` on a
# container: the names are in compose.yaml.

docker: docker-up  ## Everything with Docker alone: the bench (3001), MCP (8775), notebooks (8881)

down: docker-down  ## Stop and remove the containers

docker-build:  ## Build the images
	docker compose --profile tools build

docker-up:
	docker compose up --build

docker-down:
	docker compose --profile tools down --remove-orphans

app-up:  ## The calibration bench alone, with Docker: http://localhost:3001
	docker compose up --build taratura

docker-bench:  ## The benchmark, in a container
	docker compose run --rm --build bench

docker-python:  ## Python in a container, with rainfall_thresholds to import
	docker compose run --rm --build python
