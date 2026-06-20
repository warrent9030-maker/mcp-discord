FROM python:3.12-slim-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# 1. Copy only the dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# 2. Copy the actual source code
COPY src/ ./src/
COPY README.md ./

# 3. Install dependencies only (skip project install to avoid path issues)
RUN uv sync --frozen --no-dev --no-install-project

# Update PATH to include the virtual environment's bin and PYTHONPATH for src
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Entry point
ENTRYPOINT ["python", "-c", "import discord_mcp; discord_mcp.main()"]