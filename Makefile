.PHONY: test lint format build clean publish-test publish

test:
	uv run pytest -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

build: clean
	uv build

clean:
	rm -rf dist/ build/ *.egg-info

publish-test: build
	uv run twine upload --repository testpypi dist/*

publish: build
	uv run twine upload dist/*
