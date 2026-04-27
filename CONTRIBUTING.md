# Contributing

Thanks for your interest in improving storefront!

## Workflow

1. Fork the repo and create a topic branch off `main`.
2. Install dependencies with `uv sync` and `uv pip install ".[dev]"`.
3. Make your change. Add or update tests in `playground/tests/`.
4. Run `uv run ruff check .` and `uv run pytest --cov` locally — both must pass.
5. Open a pull request against `main` and fill in the description.

## Reporting issues

Use GitHub Issues for bugs and feature requests. For security issues, see [SECURITY.md](SECURITY.md).
