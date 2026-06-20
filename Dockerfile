FROM python:3.12-slim-bookworm

# Install uv directly
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation and set uv link mode
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY README.md ./

# Install the project and dependencies
RUN uv sync --frozen --no-dev

# Update PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Entry point
ENTRYPOINT ["mcp-discord"]