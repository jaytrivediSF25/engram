.PHONY: install test lint demo clean

install:        ## Install the CLI + Claude Code hooks
	./install.sh

test:           ## Run the test suite
	uv run pytest -q

lint:           ## Lint with ruff
	uvx ruff check src tests

demo:           ## Run the miniature end-to-end demo
	bash examples/demo.sh

clean:          ## Remove build/test artifacts
	rm -rf .pytest_cache .venv dist build *.egg-info

help:           ## Show this help
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'
