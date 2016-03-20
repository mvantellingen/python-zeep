.PHONY: install clean test retest coverage

install:
	pip install -e .[test]

clean:
	find . -name '*.pyc' -delete

test:
	py.test

retest:
	py.test --lf


coverage:
	py.test --cov=zeep --cov-report=term-missing
