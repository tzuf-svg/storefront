# storefront

## Overview

A Django REST Framework task-list API with Google OAuth authentication and a Monday.com webhook integration. Originally a todo-list exercise, the project has grown a permission model (staff-only access, category restrictions), a unified login page, and a hardened webhook receiver that executes untrusted Monday.com payloads inside a gVisor sandbox.

All business logic lives in the single Django app `playground/` (models, serializers, views, permissions, tests). Project config lives in `storefront/`.

## Setup

### Prerequisites
- Docker and Docker Compose, **or** Python 3.12+ with a local PostgreSQL.
- A Google OAuth client for login (configured via `django-allauth`).

### With Docker (recommended)
```bash
docker-compose up
```
Starts PostgreSQL on port 5433 and Django on port 8000.

### Locally
```bash
uv sync
source .venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Override `DB_HOST` / `DB_PORT` if PostgreSQL is not at `localhost:5433`.

## Usage

### Endpoints
- `/tasklist/` — HTML task list (session auth, staff only)
- `/api/tasks/` — REST API for tasks (token auth, staff only)
- `/api-auth/` — `dj-rest-auth` endpoints (login, logout, token)
- `/admin/` — Django admin
- `/monday/webhook/` — Monday.com webhook receiver (sandboxed)

### Permission model
- All endpoints require `is_staff=True`.
- Superusers see all tasks.
- Staff users see their own tasks plus tasks where they're listed as a coworker.
- Tasks with category `management` are hidden from non-superusers.

### Tests
```bash
pytest                                                            # all tests
pytest playground/tests.py                                        # one file
pytest playground/tests.py::TaskListCreateTest::test_create_task  # one test
pytest --create-db                                                # force DB recreation
```
Tests use `--reuse-db` by default and run against PostgreSQL — there is no SQLite fallback.

## Contributing

1. Branch off `main` with a topical name (`feat/...`, `fix/...`, `chore/...`).
2. Install dev deps: `uv sync`.
3. Run `pytest` and `ruff check` locally before opening a PR.
4. Keep PRs focused — one logical change per PR.
5. Open the pull request against `main`. CI runs pytest and ruff on every push.

For larger changes, open an issue first to discuss the approach.
