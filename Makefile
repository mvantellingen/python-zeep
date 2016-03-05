.PHONY: test retest

clean:
	find . -name '*.pyc' -delete

test:
	py.test

retest:
	py.test --lf


coverage:
	py.test --cov=zeep --cov-report=term-missing
