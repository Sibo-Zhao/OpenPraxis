.PHONY: build clean publish publish-test lint test help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

PYTHON ?= python3

build: clean  ## Build sdist and wheel into dist/
	$(PYTHON) -m build

clean:  ## Remove build artifacts
	rm -rf dist/ build/ src/*.egg-info src/openpraxis/*.egg-info

publish: build  ## Upload to PyPI (requires TWINE_USERNAME/TWINE_PASSWORD or ~/.pypirc)
	$(PYTHON) -m twine upload dist/*

publish-test: build  ## Upload to TestPyPI first
	$(PYTHON) -m twine upload --repository testpypi dist/*

lint:  ## Run ruff linter
	ruff check src tests

test:  ## Run pytest
	pytest
