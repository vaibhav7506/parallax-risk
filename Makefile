.PHONY: install lint typecheck docscheck test check build serve container
install:
	python -m pip install -e ".[dev]"
lint:
	python -m ruff check .
	python -m ruff format --check .
typecheck:
	python -m mypy
docscheck:
	python scripts/check_docs.py
test:
	python -m pytest
check: lint typecheck docscheck test
build:
	python -m build
serve:
	python -m uvicorn parallax_risk.api.app:create_app --factory --host 127.0.0.1 --port 8000
container:
	docker build -t parallax-risk:0.4.0 .
