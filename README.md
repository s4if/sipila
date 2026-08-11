# Sipila — Sistem Peminjaman Laptop

Sistem manajemen peminjaman laptop untuk **SMKIT Ihsanul Fikri Mungkid**.
Dibangun dengan **Flask + HTMX** (server-rendered, tanpa SPA) dengan
antarmuka sepenuhnya dalam **Bahasa Indonesia**.

## Fitur

- **Login terpisah** untuk admin/guru dan siswa (NIS + password).
- **Panel admin**: dashboard, CRUD guru, rombel, siswa (termasuk
  impor/ekspor XLSX), kategori laptop, larangan (ban) peminjaman, serta
  tinjauan permintaan (terima / tolak / batalkan).
- **Portal siswa**: mengajukan permintaan peminjaman (tanggal hari ini
  s.d. +7 hari, satu permintaan per siswa per tanggal).
- **Supervisor/monitor**: pantuan harian permintaan yang diterima,
  konfirmasi pemakaian (dipakai / tidak dipakai), dan ekspor laporan
  XLSX.
- **Peran (role)**: admin & superadmin (CRIB guru/kategori/siswa hanya
  untuk superadmin).
- **Keamanan**: hash password (pbkdf2:sha256), CSRF, sanitasi input.
- **Waktu WIB** dipin konsisten di seluruh stack (lihat
  [DEPLOYMENT.md](./DEPLOYMENT.md)).

## Teknologi

Python 3.12 · Flask · Flask-SQLAlchemy · Flask-Migrate (Alembic) ·
Flask-WTF (WTForms) · Flask-HTMX · Jinja2 · Bootstrap 5 · jQuery ·
DataTables · openpyxl · Gunicorn + Gevent · SQLite.

## Memulai (Development)

Menggunakan [`uv`](https://docs.astral.sh/uv/) untuk manajemen dependency.

```bash
# Pasang dependency
uv sync

# Jalankan server development
uv run flask --app app run --debug
```

Database SQLite berada di folder `instance/`. Saat pertama kali, jalankan
migrasi lalu buat admin awal:

```bash
uv run flask --app app db upgrade
uv run flask --app app add-admin-user --username admin --password admin123 --role superadmin
```

Buka `http://localhost:5000` (route `/` mengarah ke login admin).

## Perintah CLI

```bash
uv run flask --app app add-admin-user     --username <nama> --password <pwd> --role admin|superadmin
uv run flask --app app change-admin-user  --username <nama> --password <pwd> --role admin|superadmin
uv run flask --app app delete-admin-user  --username <nama>
```

## Migrasi Database

```bash
uv run flask --app app db migrate -m "deskripsi perubahan"
uv run flask --app app db upgrade
```

> Catatan: ada `reset_migrations.sh` yang menghapus seluruh riwayat
> migrasi dan membuat ulang dari awal — **hanya untuk development**.

## Testing

```bash
# Jalankan seluruh test
uv run pytest

# Paralel (memakai seluruh core CPU)
uv run pytest -n auto

# Dengan coverage (jalankan serial agar akurat)
uv run pytest --cov=app tests/
```

## Deployment (Docker)

```bash
docker compose up --build
```

- Port: `5000`.
- Volume: `./instance` (database) dan `./appconfig.toml` (read-only).
- Pastikan `SECRET_KEY` dan `TZ=Asia/Jakarta` diatur — lihat
  [docker-compose.yml](./docker-compose.yml).

Skrip bantu di folder `docker/`:
- `setup.sh <container_id>` — inisialisasi DB + admin awal.
- `postupdate.sh <container_id>` — migrasi setelah update.

## Dokumentasi

- [ARCHITECTURE.md](./ARCHITECTURE.md) — arsitektur aplikasi detail
  (struktur, app factory, blueprint, model, view, template, testing).
- [AGENTS.md](./AGENTS.md) — ikhtisar proyek, perintah, dan konvensi.
- [DEPLOYMENT.md](./DEPLOYMENT.md) — catatan deployment & strategi WIB.

## Lisensi

[MIT](./LICENSE) © Saiful Habib
