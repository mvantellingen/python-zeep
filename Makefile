.PHONY: test retest


test:
	py.test


retest:
	py.test --lf
