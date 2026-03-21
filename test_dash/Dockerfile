# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install uv for fast dependency resolution
RUN pip install uv

# Set the working directory
WORKDIR /app

# Install dependencies into a separate venv to avoid volume shadowing
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the dependency specification
COPY test_dash/pyproject.toml test_dash/uv.lock* ./

RUN uv sync

# Copy the game files inside the container
RUN mkdir -p /game
COPY game/entities.json /game/
COPY game/components.json /game/

# Expose port
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
