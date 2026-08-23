# ARCHITECTURE.md — Sipila Architecture

Detailed application architecture for Sipila (Sistem Peminjaman Laptop). See [AGENTS.md](./AGENTS.md) for project overview, commands, conventions, and contribution workflow.

## Project Structure

```
sipila/
├── app/                        # Main application package
│   ├── __init__.py             # create_app() factory, TZ pinning (WIB), CLI commands, blueprint registration
│   ├── config.py               # Config class + APP_CONFIG (appconfig.toml), env overrides for secrets/DB
│   ├── db.py                   # SQLAlchemy + Migrate init + PRAGMA SQLite (WAL) listener
│   ├── models.py               # All SQLAlchemy models
│   ├── helper.py               # Role decorators, hx_render, sanitize/js_escape, get_today/get_now, htmx init
│   ├── periods.py              # LoanPeriod lazy materialization (materialize_periods, get_active_period_for)
│   ├── forms.py                # WTForms form classes
│   ├── auth.py                 # Auth blueprint (admin login, siswa login, logout)
│   ├── admin.py                # Admin blueprint (dashboard, CRUD guru/rombel/siswa/kategori/larangan/permintaan)
│   ├── siswa.py                # Siswa blueprint (portal, permintaan CRUD)
│   ├── supervisor.py           # Supervisor blueprint (monitor harian, konfirmasi, export XLSX)
│   ├── pantau.py               # Pantau blueprint (monitor publik tanpa login, semua permintaan hari ini)
│   ├── static/                 # Bootstrap 5, jQuery, DataTables, htmx, Bootstrap Icons, app.js, style.css
│   └── templates/              # Jinja2 templates (.jinja)
│       ├── macros.jinja        # Shared macros (render_field, render_notif)
│       ├── login/              # Admin & siswa login pages
│       ├── admin/              # Admin panel (layout + pages)
│       ├── siswa/              # Siswa portal (layout + pages)
│       ├── supervisor/         # Monitor page
│       └── pantau/             # Halaman monitor publik (standalone, tanpa layout sesi)
├── tests/                      # pytest suite (conftest + 8 test files)
├── migrations/                 # Alembic migrations (tracked in git, initial revision)
├── docker/                     # Docker setup / post-update scripts
├── instance/                   # SQLite DB (gitignored)
├── appconfig.toml              # App-level config (app_name)
├── pyproject.toml              # Project metadata, dependencies, pytest config
├── Dockerfile                  # Production image (ENV TZ=Asia/Jakarta)
├── docker-compose.yml          # Compose stack (TZ=Asia/Jakarta, volume mounts instance/ + appconfig.toml)
├── DEPLOYMENT.md               # Deployment notes, WIB timezone strategy across the stack
└── reset_dev_db.sh            # Reset DB development (hapus instance/, db upgrade, buat admin awal)
```

## Runtime Bootstrap (App Factory)

- `create_app(test_config=None)` in `app/__init__.py` — factory pattern; `test_config` overrides `Config` (used by tests).
- **Timezone pinning**: at import time the process is pinned to `Asia/Jakarta` via `os.environ.setdefault("TZ", "Asia/Jakarta")` + `time.tzset()`, so `date.today()` / `datetime.now()` always return WIB wall-clock. The same pinning is mirrored in `Dockerfile` and `docker-compose.yml` — see [DEPLOYMENT.md](./DEPLOYMENT.md) for the full strategy.
- Extensions (`db`/`migrate`, `csrf`, `htmx`) initialized in separate modules, wired via `init_app()`.
- Context processor injects `app_name` from `APP_CONFIG` (loaded from `appconfig.toml` in `config.py`).

## SQLite Tuning (WAL & gevent)

- `app/db.py` sets PRAGMAs on every new sqlite3 connection: `journal_mode=WAL`, `synchronous=FULL` (safest durability, small write penalty), `busy_timeout=10000` (wait instead of instant `database is locked` errors across gunicorn workers).
- `SQLALCHEMY_ENGINE_OPTIONS` in `config.py` uses `NullPool` + `check_same_thread=False` + `timeout=15` — the safe pooling setup for gunicorn **gevent** workers (no connection reuse across greenlets/fork).
- WAL is persistent in the DB header; backups must include `app.db-wal`/`app.db-shm` or use `sqlite3 app.db ".backup '..."` (SQLite-aware copy).
- In-memory test DBs are unaffected: Flask-SQLAlchemy forces `StaticPool` for `:memory:`.
- Root `/` redirects to `auth.login_admin`.
- CLI commands (`add-admin-user`, `change-admin-user`, `delete-admin-user`, `materialize-periods`): the admin commands take `--username/--password/--role` (admin|superadmin); passwords hashed with pbkdf2:sha256, `salt_length=16`. `materialize-periods [--date YYYY-MM-DD]` generates daily `BorrowingRequest` rows from active `LoanPeriod`s (lazy materialization; run daily via cron — see DEPLOYMENT.md).

## Blueprints

| Blueprint | Module | url_prefix | Purpose | Guard |
|---|---|---|---|---|
| `auth` | `app/auth.py` | none | Admin login, siswa login, logout | public |
| `admin` | `app/admin.py` | `/admin` | Dashboard + CRUD guru, rombel, siswa, kategori, larangan, permintaan; XLSX template/import/export | `@admin_required` / `@superadmin_required` |
| `siswa` | `app/siswa.py` | `/siswa` | Portal beranda, permintaan (tambah/edit/batal/detail/data), logout | `@login_required` |
| `supervisor` | `app/supervisor.py` | `/supervisor` | Monitor harian, konfirmasi pemakaian, export laporan XLSX | `@admin_required` |
| `pantau` | `app/pantau.py` | `/pantau` | Monitor publik hari ini (semua status, kolom Nama/Rombel/Kategori/Status) | public |

New feature areas should be added as separate blueprints.

## Models

All models live in `app/models.py` (Flask-SQLAlchemy). `__tablename__` is explicit (plural, snake_case); every model has `__repr__`.

| Model | Table | Notes |
|---|---|---|
| `Teacher` | `teachers` | Admin/guru account: `username` (unique), `password` (hash), `is_superadmin`, `name`, `contact_person`, `is_deleted` (soft delete; username diganti `<username>#deleted#<id>` saat dihapus supaya bisa dipakai ulang) |
| `ClassGroup` | `class_groups` | `name`, `grade_level`, `major`, `homeroom_teacher_id`; `display_name` & `active_student_count` properties |
| `Student` | `students` | NIS (`student_id`, unique), `name`, `password`, `class_group_id`, `is_deleted` (soft delete), `admin_note` |
| `Category` | `categories` | Laptop category: `name` (unique), `is_deleted` (soft delete; saat dihapus `name` diganti `"[deleted]"` + suffix id bila bentrok, link `CategoryTeacher` dibersihkan, dan `LoanPeriod` aktifnya dinonaktifkan); `teacher_links` cascade delete-orphan |
| `CategoryTeacher` | `category_teachers` | M2M join Category↔Teacher (supervising teachers), `UniqueConstraint(category_id, teacher_id)` |
| `StudentBan` | `student_bans` | Larangan: `student_id`, `creator_id`, `start_date`, `end_date`, `reason`, `created_at`; `is_active`/`is_concluded` properties |
| `LoanPeriod` | `loan_periods` | Pinjaman multi-hari yang diberikan guru (bukan diajukan siswa): `student_id`, `category_id`, `start_date`/`end_date`, `note`, `is_active`, `created_by`, `created_at`, `cancelled_at`; `status_label` property (active/upcoming/concluded/cancelled). Row `BorrowingRequest` harian di-generate malas via `app/periods.py` |
| `BorrowingRequest` | `borrowing_requests` | `status` pending/accepted/rejected; review fields (`reviewed_by/at`, `teacher_note`); confirmation fields (`confirmation` used/not_used, `confirmed_by/at`); `loan_period_id` (terisi jika row digenerate dari `LoanPeriod`); `UniqueConstraint(student_id, date)` |

Conventions: foreign keys use `tablename.id`; relationships via `backref` or explicit `relationship()`; timestamp defaults are Python-side (`default=get_now`), never DB `now()`/triggers — keeps all times WIB wall-clock. Soft delete (`is_deleted`) dipakai untuk siswa, guru, dan kategori supaya riwayat tetap utuh; semua query yang menampilkan pilihan/daftar memfilter `is_deleted=False`, termasuk login (guru & siswa).

## Auth, Roles & Security

- Session keys: admin → `logged_in`, `is_admin`, `is_superadmin`, `admin_name`; siswa → `logged_in`, `is_admin=False`, `student_id`, `student_name`, `student_db_id`.
- Role decorators in `app/helper.py`:
  - `@login_required` — siswa portal; redirects to `auth.login_siswa`
  - `@admin_required` — admin panel; redirects to `auth.login_admin`
  - `@superadmin_required` — superadmin-only actions (guru CRUD, kategori tambah/edit/hapus, siswa tambah/edit/hapus/import); non-superadmins redirected to admin beranda
- Passwords hashed with `werkzeug.security.generate_password_hash` (pbkdf2:sha256, `salt_length=16`).
- CSRF protection enabled globally via Flask-WTF.
- `sanitize()` strips `<script>` tags, dangerous tags (`iframe`, `embed`, `object`, `form`, `input`, `button`, `style`, `link`, `meta`), event-handler attributes, and `javascript:` URLs. `js_escape()` escapes values interpolated into JS string literals (e.g., `onclick="fn('...')"`).

## Views (Route Handlers)

- CRUD follows a consistent pattern per entity:
  - **List**: `GET /admin/<entity>` — page shell; `GET /admin/<entity>/data` returns JSON for DataTables
  - **Add**: `GET/POST /admin/<entity>/tambah` — GET shows form, POST creates, redirects to list
  - **Edit**: `GET/POST /admin/<entity>/edit/<id>` — GET shows pre-filled form, POST updates
  - **Delete**: `POST /admin/<entity>/hapus` — soft delete for siswa (`is_deleted=True`), guru (`is_deleted=True`, username ditandai), dan kategori (`is_deleted=True`, name → `"[deleted]"`, link guru dibersihkan); hard delete for rombel (diblokir jika masih ada siswa aktif) dan larangan
- JSON endpoints (always `{"data": [...]}` for DataTables): `/rombel/data`, `/siswa/data`, `/siswa/<id>/data`, `/larangan/data`, `/guru/data`, `/kategori/data`, `/permintaan/data`, `/siswa/permintaan/data`, `/supervisor/monitor/data`, `/pantau/data`.
- Pinjaman periode (peminjaman multi-hari, hanya oleh guru): `GET/POST /admin/siswa/<id>/pinjaman-periode/tambah` (form; superadmin memilih semua kategori, guru biasa hanya kategori yang diawasnya; validasi rentang, anti-overlap, start >= hari ini; jika rentang mencakup hari ini row hari ini langsung dimaterialisasi) dan `POST /admin/pinjaman-periode/batalkan/<id>` (hanya superadmin/pembuat). Tombolnya ada di halaman detail siswa. Siswa tidak bisa mengajukan manual pada tanggal yang tercakup periode aktif.
- All page responses rendered via `hx_render()` (helper.py): injects standard context (`username`, `is_superadmin`, `student_name`, `is_htmx`) and, when `push_url=` is given, sets the `HX-Push-Url` header (accepts an endpoint name like `"siswa.beranda"` or a path).
- Notifications passed as `notif` dict with keys `error`, `success`, `info`, rendered via `render_notif` macro.
- Permintaan review is category-scoped: `_teacher_can_review(teacher_id, category_id)` restricts review to teachers linked to the request's category via `CategoryTeacher`; pending requests past their date are treated as `expired` (`_is_kadaluarsa`).

## Templates & HTMX

- `.jinja` extension (NOT `.html`).
- Section layouts: `admin/layout.jinja`, `siswa/layout.jinja`, `login/layout.jinja`; pages `{% extends %}` their section layout.
- Body carries `hx-boost="true" hx-push-url="true"`; sidebar links and topbar swap content into `#hx_content` via `hx-target="#hx_content" hx-swap="innerHTML"`.
- Shared macros in `macros.jinja` — import with `{% from 'macros.jinja' import render_field, render_notif %}`.
- List pages use **DataTables** (jQuery plugin) fed by JSON `/data` endpoints; DataTables, Bootstrap, jQuery, and htmx are served from `app/static/`, Bootstrap Icons from CDN.
- CSRF tokens via Flask-WTF (auto-handled in forms).

## Forms

- WTForms classes in `app/forms.py`, `FlaskForm` base; field names match model attribute names.
- LoginForm, SiswaLoginForm, GantiPasswordForm, PermintaanSiswaForm, GuruForm, SiswaForm, RombelForm, StudentBanForm, KategoriForm (uses `SelectMultipleField` for supervising teachers).

## Permintaan (Borrowing) Flow

1. **Siswa portal** (`siswa` blueprint): student logs in with NIS + password. Request date window is today → +7 days (`_date_range()`); one request per student per date (enforced in code and by DB unique constraint). Only `pending` requests can be edited/cancelled. A student with an active ban cannot submit/edit.
2. **Review** (`admin` blueprint): admin/teacher accepts (`terima`), rejects (`tolak`), or cancels (`batalkan`) pending requests; reviewer and timestamp recorded on `reviewed_by`/`reviewed_at`, feedback in `teacher_note`.
3. **Confirmation** (`supervisor` blueprint): once accepted, the daily monitor records whether the laptop was actually used — `used`/`not_used` on `confirmation` + `confirmed_by`/`confirmed_at`.

## Supervisor Monitor & Export

- `/supervisor/monitor` shows all `accepted` requests for a chosen date (window ±365 days); `/monitor/data` returns DataTables JSON.
- `/monitor/export` builds an XLSX report (openpyxl) for a date range with an optional "hanya_digunakan" filter (only confirmed `used`).
- Konfirmasi endpoints: `/monitor/konfirmasi/<id>` and `/monitor/batalkan_konfirmasi/<id>` (JSON responses).

## Pantau (Monitor Publik)

- `/pantau` adalah halaman publik tanpa login untuk guru melihat sekilas semua permintaan peminjaman **hari ini** (semua status: pending/accepted/rejected), termasuk row hasil materialisasi `LoanPeriod`.
- Kolom: Nama, Rombel, Kategori, Status (badge). Tidak menampilkan NIS/catatan/data sensitif lain.
- `/pantau/data` selalu mengembalikan hari ini (tanpa parameter tanggal); template standalone (tanpa layout admin/siswa) dengan auto-refresh DataTables tiap 30 detik.

## XLSX Import/Export (admin)

- `/admin/siswa/template` — downloadable XLSX template with mode/jumlah options (skip|update) and rombel id reference sheet.
- `/admin/siswa/import` — bulk import siswa from uploaded `.xlsx` (skip or update existing NIS).
- `/admin/siswa/<id>/export` — per-student history export to XLSX.

## Testing

- Tests in `tests/`, auto-discovered via pytest config in `pyproject.toml`.
- `conftest.py` fixtures: `app` (in-memory SQLite, CSRF disabled), `client`, `runner`, `admin_user`, `logged_in_client`, `regular_admin`, `regular_admin_client`, `siswa_user`, `logged_in_siswa_client`, `kategori_with_teacher`, `borrowing_request`, `student_ban`, `concluded_student_ban`, `ban_by_regular_admin`.
- Test files: `test_auth`, `test_admin`, `test_category`, `test_helper`, `test_models`, `test_permintaan`, `test_siswa`, `test_supervisor`, `test_pantau`.
- Flat test functions (no classes) except grouped tests (e.g., `TestSanitizeInput`); naming `test_<what>_<condition>`.
- Assertions check status codes, response content, JSON payloads, and redirect locations.
- **Parallelization**: `-n auto` (pytest-xdist) is safe because the `app` fixture is function-scoped with an in-memory SQLite DB per test — no cross-test or cross-worker state. Drop to serial (`pytest --cov=app tests/`) when collecting coverage, since `pytest-cov` measures more accurately in a single process.
