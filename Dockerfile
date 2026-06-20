FROM python:3.12-slim-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# 1. Copy pyproject.toml first
COPY pyproject.toml ./

# 2. Install dependencies (it will generate a lockfile on the fly since we aren't using --frozen or copying uv.lock)
RUN uv sync --no-dev --no-install-project

# 3. Copy the actual source code
COPY src/ ./src/
COPY README.md ./

# Update PATH to include the virtual environment's bin and PYTHONPATH for src
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Entry point using the virtual environment's python
ENTRYPOINT ["/app/.venv/bin/python", "-c", "import discord_mcp; discord_mcp.main()"]
