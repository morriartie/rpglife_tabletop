.PHONY: setup run dash-run test docker-run docker-stop docker-test

setup:
	cd api && uv sync
	cd test_dash && uv sync

run:
	PYTHONPATH=. uv run --project api uvicorn api.src.main:app --host 0.0.0.0 --port 8001 --reload

dash-run:
	cd test_dash && uv run streamlit run app.py

test:
	PYTHONPATH=. uv run --project api pytest api/src/tests/

docker-run:
	docker-compose up -d --build

docker-stop:
	docker-compose down

docker-test:
	docker-compose run --rm api pytest api/src/tests/
