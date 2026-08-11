# AGENTS.md — Sipila (Sistem Peminjaman Laptop)

## Project Overview

Sipila is a Flask-based laptop lending management system for SMKIT Ihsanul Fikri Mungkid. It uses Flask + HTMX for server-rendered dynamic UI (no SPA framework). The app is entirely in **Bahasa Indonesia** for UI strings and route names.

## Tech Stack

- **Python 3.12** (managed via `uv`, lockfile: `uv.lock`)
- **Flask** with Blueprints for routing
- **Flask-SQLAlchemy** + **Flask-Migrate** (Alembic) for ORM and migrations
- **Flask-WTF** + **WTForms** for form handling with CSRF protection
- **Flask-HTMX** for HTMX integration
- **Jinja2** templates (`.jinja` extension, NOT `.html`)
- **Bootstrap 5** + **jQuery** + **DataTables** (static assets); **Bootstrap Icons** via CDN
- **openpyxl** for XLSX template/import/export (bulk import siswa, laporan monitor)
- **Gunicorn + Gevent** for production (Docker)
- **SQLite** (instance folder) for database
- **pytest + pytest-cov + pytest-xdist** for testing (parallelizable)

## Commands

```bash
# Install dependencies
uv sync

# Run dev server
uv run flask --app app run --debug

# Run tests
uv run pytest

# Run tests in parallel (uses all CPU cores)
uv run pytest -n auto

# Run tests with coverage (parallelization is slower with coverage; use serial)
uv run pytest --cov=app tests/

# Pin worker count
uv run pytest -n 4

# Database migrations
uv run flask --app app db migrate -m "description"
uv run flask --app app db upgrade

# CLI commands (defined in app/__init__.py)
uv run flask --app app add-admin-user
uv run flask --app app change-admin-user
uv run flask --app app delete-admin-user

# Docker
docker compose up --build
```

## Architecture

The detailed application architecture — project structure, app factory, blueprints, models, views, templates, auth/security, forms, and testing patterns — lives in [ARCHITECTURE.md](./ARCHITECTURE.md). Read it before making structural changes.

## Conventions

- **Language**: All UI text, route names, comments in Bahasa Indonesia (e.g., `tambah`, `hapus`, `ganti_password`, `beranda`, `siswa`, `rombel`)
- **Imports**: stdlib → third-party → local; avoid circular imports by using late imports inside functions
- **No type annotations** in current codebase
- **Comments**: add simple comments when necessary to clarify non-obvious logic; keep them concise and in Bahasa Indonesia where appropriate
- **Single quotes** not enforced — both single and double quotes used; be consistent within a file
- **Template variables**: render pages via `hx_render()` in `helper.py` so standard context (`username`, `is_superadmin`, `student_name`, `is_htmx`) is injected automatically; templates read `{{ username }}`, not `admin_name`
- **Config**: app-level settings in `appconfig.toml`, secrets via environment variables or instance config
- **Migrations**: tracked in `migrations/` via Flask-Migrate/Alembic

## Adding New Features

1. Add model to `app/models.py` with `__tablename__` and `__repr__`
2. Run `flask --app app db migrate -m "add <model>"` and `flask --app app db upgrade`
3. Create a new blueprint file in `app/` (or extend `admin.py`)
4. Register blueprint in `create_app()` in `app/__init__.py`
5. Add templates in `app/templates/<section>/` extending the appropriate layout
6. Add WTForms in `app/forms.py` if needed
7. Add tests in `tests/` using existing fixtures from `conftest.py`
8. Run `pytest` to verify
