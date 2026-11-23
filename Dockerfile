# rainfall-thresholds with the example notebooks and the benchmark.
#
#   docker compose up            the notebooks, on http://localhost:8888
#   make docker-bench            the benchmark
#
# No fixed names: Compose names the image and the containers after the
# project (the folder, or COMPOSE_PROJECT_NAME), so copies never clash.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv

# Notebook 04 reads the radar with dpc-radar: rasterio brings its own GDAL,
# which needs libexpat from the system.
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app

# The dependencies first: this layer is rebuilt only when they change.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --group examples --no-install-project

COPY README.md LICENSE ./
COPY src src
RUN uv sync --locked --no-dev --group examples --no-editable

# What the notebooks and the benchmark read, at the same relative paths.
COPY benchmarks benchmarks
COPY tests/fixtures tests/fixtures
COPY notebooks notebooks

RUN python -c "import rainfall_thresholds, matplotlib, jupyterlab; print(rainfall_thresholds.__version__)"

EXPOSE 8888
WORKDIR /app/notebooks
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", \
     "--ServerApp.token=", "--ServerApp.password=", "--ServerApp.root_dir=/app"]
