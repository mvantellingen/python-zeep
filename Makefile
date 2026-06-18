.PHONY: install clean test test-all retest coverage docs lint format build

install:
	uv sync --extra docs --extra async

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete

test:
	uv run pytest -vvv

test-all:
	for v in 3.10 3.11 3.12 3.13 3.14; do \
	  UV_PROJECT_ENVIRONMENT=.venv-py$$v uv run --python $$v --extra async pytest || exit 1; \
	done

retest:
	uv run pytest -vvv --lf

coverage:
	uv run pytest --cov=zeep --cov-report=term-missing --cov-report=html

format:
	uv run ruff check --fix src tests
	uv run ruff format src tests

docs:
	$(MAKE) -C docs html

build:
	rm -rf build/* dist/*
	uv build
