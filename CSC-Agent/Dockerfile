# Stage 1: Build Environment - Install dependencies and prepare application
FROM python:3.12-slim AS build-env

# Set work directory for the build stage
WORKDIR /app

# Install system build dependencies required for many Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally in this build stage
# This ensures 'uv' executable is directly in /usr/local/bin
RUN pip install --upgrade pip
RUN pip install uv

# Copy the necessary project files for dependency resolution and building.
COPY pyproject.toml uv.lock README.md ./
COPY app ./app

# Create a temporary virtual environment for 'uv sync' to operate within.
# This keeps the dependency installation isolated from the build-env's global Python.
ENV VIRTUAL_ENV=/venv
RUN python -m venv ${VIRTUAL_ENV}
# Add venv bin to PATH for uv to use it
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

# Set environment variables for uv (relevant for the install process)
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies strictly from uv.lock into the virtual environment
# --no-dev ensures only production dependencies are installed
RUN uv sync --no-dev


# Stage 2: Production Environment - Copy installed packages and application code
FROM python:3.12-slim

# Set work directory for the final application
WORKDIR /opt/app-root

# Copy installed packages from the build-env's virtual environment
COPY --from=build-env /venv/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy the 'uv' executable from the build-env's *global* /usr/local/bin
# This is where 'pip install uv' would place it system-wide in the build-env.
COPY --from=build-env /usr/local/bin/uv /usr/local/bin/uv

# Explicitly set the PATH to include /usr/local/bin for the non-root user
ENV PATH="/usr/local/bin:$PATH"

# Copy the application code itself
COPY . /opt/app-root

# Correct permissions for the app-root directory
RUN useradd -m appuser \
    && chown -R appuser:appuser /opt/app-root

# Expose default port
EXPOSE 10005

# Switch to non-root user
USER appuser

# FINAL FIX: Remove '--system' from CMD.
# uv run will automatically use the global Python environment as we've installed
# dependencies there and ensured 'uv' is in PATH. The '--system' flag is not for uv run.
CMD ["uv", "run", "app", "--host", "0.0.0.0", "--port", "10005"]