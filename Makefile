.PHONY: check lint format typecheck test bench build figures docs notebooks \
        docker-build docker-up docker-down docker-bench docker-python app app-test app-up

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
	uv run python -m benchmarks.faithful --check

build:
	uv build

figures:
	uv run --with matplotlib python docs/make_figures.py

docs:
	uv run --group docs zensical build --strict
	uv run --group docs python tools/build_llms.py

# Run every notebook again and save the results. 04 needs the network.
notebooks:
	cd notebooks && uv run --group examples jupyter nbconvert --to notebook --execute --inplace *.ipynb

# Docker. Every target goes through `docker compose`, never a container by
# name: the names come from the project (this folder, or COMPOSE_PROJECT_NAME).
docker-build:
	docker compose --profile tools build

docker-up:
	docker compose up --build

docker-down:
	docker compose --profile tools down --remove-orphans

docker-bench:
	docker compose run --rm --build bench

docker-python:
	docker compose run --rm --build python

# The calibration bench (app/): locally with uv and npm, or with Docker.
app:
	sh app/vendor.sh
	cd app && uv run uvicorn taratura.api:app --reload

app-test:
	cd app && uv run pytest

app-up:
	docker compose up --build taratura

