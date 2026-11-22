.PHONY: run lint format test

run:
	PYTHONPATH=src .venv/bin/python -m std_bot

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	.venv/bin/basedpyright

format:
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .

test:
	.venv/bin/pytest -q
