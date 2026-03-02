.PHONY: install lint test run

install:
	python -m pip install -r requirements.txt

test:
	pytest

lint:
	ruff check app tests

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
