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
- **Bootstrap 5** + **Bootstrap Icons** + **jQuery** (served as static assets)
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

## Project Structure

```
sipila/
├── app/                    # Main application package
│   ├── __init__.py         # create_app() factory, CLI commands, blueprint registration
│   ├── config.py           # Config class, reads appconfig.toml
│   ├── db.py               # SQLAlchemy + Migrate init
│   ├── models.py           # All SQLAlchemy models
│   ├── auth.py             # Auth blueprint (login/logout)
│   ├── admin.py            # Admin blueprint (dashboard, CRUD routes)
│   ├── forms.py            # WTForms form classes
│   ├── helper.py           # Decorators (login_required, admin_required), sanitize, htmx init
│   └── templates/          # Jinja2 templates
│       ├── macros.jinja    # Shared macros (render_field, render_notif)
│       ├── login/          # Login page templates
│       └── admin/          # Admin panel templates (layout + pages)
├── tests/                  # pytest test suite
│   ├── conftest.py         # Fixtures: app, client, runner, admin_user, logged_in_client
│   ├── test_auth.py
│   ├── test_admin.py
│   ├── test_models.py
│   └── test_helper.py
├── migrations/             # Alembic migrations
├── docker/                 # Docker setup scripts
├── instance/               # SQLite DB (gitignored)
├── appconfig.toml          # App-level config (app_name, etc.)
├── pyproject.toml          # Project metadata, dependencies, pytest config
└── Dockerfile              # Production Docker image
```

## Architecture Patterns

### App Factory
- `create_app(test_config=None)` in `app/__init__.py` — always use the factory pattern
- Extensions (db, csrf, htmx) are initialized in separate modules and wired via `init_app()`

### Blueprints
- `auth` (`app/auth.py`): Login/logout routes, no url_prefix
- `admin` (`app/admin.py`): All admin CRUD routes, `url_prefix='/admin'`
- New feature areas should be added as separate blueprints

### Models
- All models in `app/models.py` using Flask-SQLAlchemy declarative base
- `__tablename__` explicitly set (plural, snake_case)
- `__repr__` method on every model
- Foreign keys use `tablename.id` convention
- Relationships use `backref` or explicit `relationship()`

### Views (Route Handlers)
- CRUD follows a consistent pattern per entity:
  - **List**: `GET /entity` — queries all, renders list template
  - **Add**: `GET/POST /entity/tambah` — GET shows form, POST creates and redirects to list
  - **Edit**: `GET/POST /entity/edit/<id>` — GET shows form pre-filled, POST updates
  - **Delete**: `POST /entity/hapus` — soft or hard delete, redirects to list
- All admin routes use `@admin_required` decorator
- HTMX responses use `make_response()` with `HX-Push-Url` header for URL updates
- Notifications passed as `notif` dict with keys `error`, `success`, `info` rendered via `render_notif` macro
- Templates receive `admin_name`, `is_htmx` as standard context variables

### Templates
- Use `.jinja` file extension (NOT `.html`)
- Each section has a `layout.jinja` for the base layout
- Content pages extend their section's layout via `{% extends %}`
- Shared macros in `macros.jinja` — import with `{% from 'macros.jinja' import render_field, render_notif %}`
- HTMX: `hx-boost="true"` on body, `hx-target="#hx_content"` for content swapping
- CSRF tokens via Flask-WTF (auto-handled in forms)

### Auth & Security
- Session-based auth: `session['logged_in']`, `session['is_admin']`, `session['admin_name']`
- Passwords hashed with `werkzeug.security.generate_password_hash` (pbkdf2:sha256, salt_length=16)
- `admin_required` decorator in `helper.py` protects admin routes
- `login_required` decorator exists for future student auth
- CSRF protection enabled globally via Flask-WTF
- Input sanitization via `sanitize()` in `helper.py`

### Forms
- WTForms classes in `app/forms.py`
- Use `FlaskForm` as base class
- Field names match model attribute names

### Testing
- Tests in `tests/` directory, auto-discovered via pytest config in `pyproject.toml`
- `conftest.py` provides fixtures: `app` (in-memory SQLite, CSRF disabled), `client`, `runner`, `admin_user`, `logged_in_client`
- Test functions are flat (no classes) except for grouped tests (e.g., `TestSanitizeInput`)
- Test naming: `test_<what>_<condition>` (e.g., `test_login_valid_credentials`)
- Assertions check status codes, response content, and redirect locations
- **Parallelization**: use `-n auto` (pytest-xdist) to run across all CPU cores. Safe by default because the `app` fixture is function-scoped with an in-memory SQLite DB per test — no cross-test or cross-worker state is shared. Prefer `-n auto` for fast feedback; drop it (run serial) when collecting coverage, since `pytest-cov` measures more accurately in a single process. Keep new tests isolated (no module-level mutable state, no reliance on test execution order) so they remain parallel-safe.

## Conventions

- **Language**: All UI text, route names, comments in Bahasa Indonesia (e.g., `tambah`, `hapus`, `ganti_password`, `beranda`, `siswa`, `rombel`)
- **Imports**: stdlib → third-party → local; avoid circular imports by using late imports inside functions
- **No type annotations** in current codebase
- **Comments**: add simple comments when necessary to clarify non-obvious logic; keep them concise and in Bahasa Indonesia where appropriate
- **Single quotes** not enforced — both single and double quotes used; be consistent within a file
- **Template variables**: always pass `admin_name` and `is_htmx` to admin templates
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
