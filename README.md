# Tabletop RPG API & Dashboard

## Running via Docker (Recommended)

After cloning the repository, the easiest way to launch both the API and the testing dashboard is via Docker:

```bash
make docker-run
```

This will build the images and start both containers in the background. Once running, you can access the dashboard in your browser at `http://localhost:8501`.

When you are done, you can shut down the containers with:

```bash
make docker-stop
```

## Running Locally (Without Docker)

If you prefer to run the services locally on your machine using `uv`, you can use the following commands:

```bash
make setup
make run
make dash-run
```

**Note:** You will need to run `make run` and `make dash-run` in separate terminal windows.

### 1. Setup

The `make setup` command prepares the environment for both the API server and the testing dashboard. It manages the virtual environment using `uv` and installs the required dependencies.

### 2. API Server

The API server connects the backend game logic (in `/game`) with the web interface. The `make run` command will start the API server locally.

*Note: The API runs on port 8001 by default, which is where the dashboard expects to find it.*

### 3. Dashboard

The dashboard is built with Streamlit and has its own dependencies. The `make dash-run` command will start it.

The dashboard will open automatically in your browser at `http://localhost:8501`.
