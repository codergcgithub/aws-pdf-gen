.PHONY: install build run clean help

# ===================================================================================
# HELP
# ===================================================================================

help:
	@echo "Commands:"
	@echo "  install        : install python dependencies"
	@echo "  install-dev    : install dev dependencies"
	@echo "  test           : run tests"
	@echo "  build          : build the lambda function and layer"
	@echo "  run            : run the web server locally"
	@echo "  clean          : clean up build artifacts"

# ===================================================================================
# DEVELOPMENT
# ===================================================================================

install:
	@echo "Installing dependencies..."
	.venv/bin/python3 -m pip install -r requirements.txt

install-dev:
	@echo "Installing dev dependencies..."
	.venv/bin/python3 -m pip install -r requirements-dev.txt

run:
	@echo "Starting web server..."
	.venv/bin/uvicorn main:app --reload

test:
	.venv/bin/python3 -m pytest

# ===================================================================================
# BUILD
# ===================================================================================

build:
	@echo "Building lambda function and layer..."
	./scripts/build_lambda.sh

# ===================================================================================
# CLEAN
# ===================================================================================

clean:
	@echo "Cleaning up..."
	rm -rf dist
	rm -f .coverage
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
