# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the App

**With Docker (recommended):**
```bash
docker-compose up
```
This starts PostgreSQL on port 5433 and Django on port 8000.

**Locally:**
```bash
python manage.py runserver
```
Requires PostgreSQL running locally or set `DB_HOST`/`DB_PORT` env vars.

### Database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### Tests

```bash
pytest                          # Run all tests (--reuse-db is set by default)
pytest playground/tests.py      # Run all tests in file
pytest playground/tests.py::TaskListCreateTest::test_create_task  # Single test
pytest -v                       # Verbose output
pytest --create-db              # Force database recreation
```

Tests use `pytest-django` with `--reuse-db` configured in `pyproject.toml` for faster reruns.

## Architecture

This is a Django REST Framework task management API with Google OAuth authentication.

### Key Apps & Files

- **`storefront/`** — Django project config (settings, main urls)
- **`playground/`** — The single main app containing all business logic

### Authentication Flow

Google OAuth via `django-allauth` → redirects to `/tasklist/` on success. Session-based auth for the HTML view, token-based for the API. The `dj-rest-auth` package provides `/api-auth/` endpoints.

### Permission Model

All API endpoints require `is_staff=True` (via `playground/permissions.py`). Access filtering:
- Superusers see all tasks
- Staff users see only their own tasks + tasks where they're a coworker
- Tasks with category "management" are hidden from non-superusers

### Core Model: `ListTzuf`

The main task model (`playground/models.py`) with notable constraints:
- Title: 3–100 characters
- Due date: must be a future weekday (no weekends, no today/past); default is 1 week from today (skipping weekends), defined in `workrules.py`
- Categories: "urgent" and "management" restricted to staff users (enforced in serializer via `validate_category_logic()`)
- `completed_at` timestamp is auto-set/cleared via model `save()` override

### Database

PostgreSQL in production/Docker. Settings read `DB_HOST` (default: localhost) and `DB_PORT` (default: 5433) from environment variables. SQLite is not used; tests run against PostgreSQL.

### Test Factories

`playground/factories.py` uses `factory_boy` (`UserFactory`, `TodoFactory`) for generating test data. Tests use `APIClient.force_authenticate()` rather than going through the login flow.
