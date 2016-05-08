.PHONY: install clean test retest coverage docs

install:
	pip install -e .[test]

lint:
	flake8 src/ tests/
	isort --recursive --check-only --diff src tests

clean:
	find . -name '*.pyc' -delete

test:
	py.test -vvv

retest:
	py.test --lf

coverage:
	py.test --cov=zeep --cov-report=term-missing

docs:
	$(MAKE) -C docs html

release:
	pip install twine wheel
	rm -rf dist/*
	python setup.py sdist bdist_wheel
	twine upload -s dist/*
