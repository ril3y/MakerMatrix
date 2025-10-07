.PHONY: help test test-python test-frontend lint vulture dead-code quality install-dev

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-dev:  ## Install development dependencies
	cd MakerMatrix/frontend && npm install
	source venv_test/bin/activate && pip install -e ".[dev]" && pip install vulture

test: test-python test-frontend  ## Run all tests

test-python:  ## Run Python tests
	source venv_test/bin/activate && pytest MakerMatrix/tests

test-frontend:  ## Run frontend tests
	cd MakerMatrix/frontend && npm run test:run

lint:  ## Run linters
	cd MakerMatrix/frontend && npm run lint
	source venv_test/bin/activate && python -m pylint MakerMatrix/ || true

vulture:  ## Run vulture dead code analysis
	@echo "🔍 Running dead code analysis..."
	source venv_test/bin/activate && vulture MakerMatrix/ --config vulture.toml --sort-by-size

dead-code: vulture  ## Alias for vulture

quality: lint vulture  ## Run all quality checks

format:  ## Format code
	cd MakerMatrix/frontend && npm run format

.DEFAULT_GOAL := help
