FROM python:3.12.1

# Set work directory
WORKDIR /opt/app-root

# Copy Python Project Files (Container context must be the `python` directory)
COPY . /opt/app-root

USER root

# Install system build dependencies and UV package manager
RUN apt-get update && apt-get install -y \
    gcc g++ \
    curl gnupg2 lsb-release \
    && pip install uv

# Install Microsoft SQL Server ODBC driver for Debian
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg \
    && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get install -y unixodbc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for uv:
# UV_COMPILE_BYTECODE=1: Compiles Python files to .pyc for faster startup
# UV_LINK_MODE=copy: Ensures files are copied, not symlinked, which can avoid issues
# UV_CACHE_DIR: Set cache directory to writable location
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/opt/app-root/.cache/uv

# Install dependencies using uv sync.
# Remove --frozen temporarily to allow uv to update the lock file with new packages
# --no-install-project: Prevents installing the project itself in this stage
# --no-dev: Excludes development dependencies
# --mount=type=cache: Leverages Docker's build cache for uv, speeding up repeated builds
RUN --mount=type=cache,target=/opt/app-root/.cache/uv \
    uv sync --no-install-project --no-dev

# Install the project
RUN --mount=type=cache,target=/opt/app-root/.cache/uv \
    uv sync --no-dev

# Allow non-root user to access the everything in app-root
# RUN chgrp -R root /opt/app-root/ && chmod -R g+rwx /opt/app-root/ 

RUN mkdir -p /.cache/
RUN chown -R 1000:1000 /.cache /opt

# Expose default port (change if needed)
EXPOSE 10000

USER 1000

# Run the agent
CMD uv run app --host 0.0.0.0 --port 10000