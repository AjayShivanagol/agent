FROM python:3.12-slim

# Set work directory
WORKDIR /opt/app-root/ui

# Copy Python Project Files
# This assumes the build context is the 'ui' directory.
COPY . .

USER root

# Install system build dependencies, CA certificates, and UV package manager
RUN apt-get update && apt-get install -y build-essential ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip install uv

# Copy and install corporate CA certificates
COPY ca-certs/*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates

# Set environment variables for uv:
ENV XDG_CACHE_HOME=/opt/app-root/ui/.cache
# UV_COMPILE_BYTECODE=1: Compiles Python files to .pyc for faster startup
# UV_LINK_MODE=copy: Ensures files are copied, not symlinked, which can avoid issues
# SSL_CERT_FILE: Ensures Python uses the updated system CA bundle
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Install dependencies using uv sync.
# --frozen: Ensures uv respects the uv.lock file
# --no-install-project: Prevents installing the project itself in this stage
# --no-dev: Excludes development dependencies
# --mount=type=cache: Leverages Docker's build cache for uv, speeding up repeated builds
RUN --mount=type=cache,target=/opt/app-root/ui/.cache/uv \
    uv sync --frozen --no-dev

# Install the project
RUN --mount=type=cache,target=/opt/app-root/ui/.cache/uv \
    uv sync --frozen --no-dev

# Allow non-root user to access the everything in app-root
RUN chgrp -R root /opt/app-root/ && chmod -R g+rwx /opt/app-root/

# Expose default port (change if needed)
EXPOSE 12000

USER 1000

# Run the agent
CMD ["uv", "run", "main.py", "--host", "0.0.0.0"]
