.DEFAULT_GOAL := all
isort = isort -rc sasstastic tests
black = black -S -l 120 --target-version py37 sasstastic tests

.PHONY: install
install:
	python -m pip install -U setuptools pip
	pip install -U -r requirements.txt
	pip install -U -e .

.PHONY: format
format:
	$(isort)
	$(black)

.PHONY: lint
lint:
	flake8 sasstastic/ tests/
	$(isort) --check-only -df
	$(black) --check

.PHONY: test
test:
	pytest --cov=sasstastic

.PHONY: testcov
testcov:
	pytest --cov=sasstastic
	@echo "building coverage html"
	@coverage html

.PHONY: check-dist
check-dist:
	python setup.py check -ms
	python setup.py sdist
	twine check dist/*

.PHONY: all
all: lint testcov

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf dist
	python setup.py clean
