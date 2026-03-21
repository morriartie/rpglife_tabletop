FROM python:3.11-slim

WORKDIR /app

# Install uv and sync dependencies to a separate venv to avoid volume shadowing
RUN pip install uv
COPY api/pyproject.toml api/uv.lock* ./
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync

# The application code will be mounted as volumes in docker-compose
CMD ["uvicorn", "api.src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
