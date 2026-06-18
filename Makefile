.PHONY: install clean test retest coverage docs

install:
	pip install -e .[docs,test,async]
	pip install bumpversion twine wheel

lint:
	ruff check src tests
	ruff format --check src tests

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete

test:
	pytest -vvv

retest:
	pytest -vvv --lf

coverage:
	pytest --cov=zeep --cov-report=term-missing --cov-report=html

format:
	ruff check --fix src tests
	ruff format src tests

docs:
	$(MAKE) -C docs html

release:
	pip install twine wheel
	rm -rf build/* dist/*
	python setup.py sdist bdist_wheel
	twine upload -s dist/*
