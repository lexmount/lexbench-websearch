.PHONY: check test lint package-check
check: lint test
lint:
	uv run --frozen ruff check src tests
	uv run --frozen ruff format --check src tests
test:
	uv run --frozen python -m pytest
package-check:
	uv run --frozen python -m build
