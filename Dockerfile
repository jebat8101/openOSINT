FROM python:3.12-slim

WORKDIR /app

# Install system build deps needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY openosint/ ./openosint/

# Install the package and its dependencies
RUN pip install --no-cache-dir -e .

# Install optional OSINT binaries available via pip
RUN pip install --no-cache-dir holehe sherlock-project sublist3r

# Anthropic API key placeholder — override at runtime via -e or docker-compose
ENV ANTHROPIC_API_KEY=""

# Reports directory (mounted as a volume in docker-compose)
RUN mkdir -p /app/reports

ENTRYPOINT ["openosint"]
