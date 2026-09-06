# Catatan Deployment

## Migrasi Database

Riwayat migrasi Alembic (`migrations/`) dilacak di git dan ikut ter-bake
ke dalam image Docker (via `COPY . /app` di Dockerfile). Tidak ada bind
mount `./migrations` — deploy migrasi baru selalu lewat rebuild image:

```bash
git pull
docker compose up --build
./docker/postupdate.sh <container_id>   # flask db upgrade di dalam container
```

Setup pertama kali pakai `./docker/setup.sh <container_id>` (migrasi +
admin awal). Karena revisi migrasi hanya berlaku untuk satu riwayat,
jangan pernah menghapus/membuat ulang `migrations/` di satu sisi saja
(dev vs prod) — DB yang sudah di-upgrade dengan riwayat lama harus
di-reset jika riwayatnya diganti total.

## Timezone: Asia/Jakarta (WIB) di seluruh stack

Aplikasi menyimpan dan memproses waktu sebagai **datetime naive** yang nilainya selalu merupakan wall-clock WIB. Tidak ada konversi timezone di level aplikasi. Konsistensi dijamin dengan **mem-pin timezone proses ke `Asia/Jakarta`** di tiga lapis:

1. **Saat aplikasi start** — `app/__init__.py` memanggil `os.environ.setdefault("TZ", "Asia/Jakarta")` lalu `time.tzset()` sebelum modul lain dipakai.
2. **Image Docker** — `ENV TZ=Asia/Jakarta` di `Dockerfile`.
3. **docker-compose** — `TZ: Asia/Jakarta` di `docker-compose.yml`.

Dengan demikian `date.today()` dan `datetime.now()` di seluruh kode selalu mengembalikan waktu WIB. Akses waktu terpusat via helper `get_today()` / `get_now()` di `app/helper.py` — ini satu-satunya seam waktu dan satu-satunya tempat yang perlu diaudit.

### Implikasi penting

- **Semua insert timestamp HARUS lewat proses Python.** Jangan gunakan `DEFAULT NOW()` / `CURRENT_TIMESTAMP` / `server_default=func.now()` di sisi database, dan hindari trigger yang menulis kolom waktu, karena itu memakai jam DB sendiri yang bisa berbeda dari WIB. Default model saat ini semuanya Python-side (`default=get_now`).
- **Database server timezone tidak relevan** untuk app ini karena semua kolom waktu adalah `DateTime` / `Date` tanpa timezone (`TIMESTAMP WITHOUT TIME ZONE` di PostgreSQL). Setting `timezone` PostgreSQL hanya mempengaruhi kolom `WITH TIME ZONE` dan fungsi SQL seperti `NOW()` — keduanya tidak dipakai.

### SQLite (Development)

SQLite tidak punya konsep timezone; ia menyimpan literal yang diberikan Python (yaitu WIB wall-clock). Tidak ada konfigurasi tambahan.

### PostgreSQL (Production)

```sql
-- Opsional: set timezone DB agar konsisten (tidak wajib untuk app ini,
-- karena kolom datetime kita tanpa timezone). Hanya berguna jika Anda
-- menjalankan query SQL mentah dengan NOW()/CURRENT_TIMESTAMP.
ALTER DATABASE sipila SET timezone TO 'Asia/Jakarta';
```

### Docker

Container harus berjalan dengan `TZ=Asia/Jakarta` (sudah diatur di `Dockerfile` dan `docker-compose.yml`).

```yaml
# docker-compose.yml
environment:
  TZ: Asia/Jakarta   # WAJIB, jangan dihapus
```

## Permintaan harian dari pinjaman periode (tanpa cron)

Peminjaman jangka panjang (`LoanPeriod`) yang diberikan guru tidak langsung membuat
row `BorrowingRequest`. Row harian dibuat **malas** lewat tiga jalur:

1. **Otomatis di request pertama setiap hari** — hook `before_request` di
   `create_app()` menjalankan `ensure_today_materialized()` (lihat `app/periods.py`).
   Sebuah flag in-memory membuatnya jalan maksimal sekali per hari per proses
   (gunicorn worker); biaya per request berikutnya hanya perbandingan tanggal.
   Idempotent, jadi aman jika beberapa worker mengeksekusinya bersamaan. Jalur ini
   adalah pengganti cron — cocok untuk deployment Docker tanpa akses cron host.
2. **Saat guru membuat/mengedit periode yang mencakup hari ini** — row hari ini
   langsung dibuat di request yang sama, jadi tidak ada celah jam antara
   pembuatan periode dan request pertama hari itu.
3. **CLI manual** untuk backfill tanggal yang terlewat (mis. database baru
   di-restore dari backup):

```bash
uv run flask --app app materialize-periods            # untuk hari ini
uv run flask --app app materialize-periods --date 2026-08-22   # utk tanggal tertentu
# di dalam container production:
docker compose exec -T app flask --app app materialize-periods
```

Catatan:
- Hari ketika siswa sedang dalam masa larangan (`StudentBan`) otomatis dilewati.
- Cron luar (mis. 00:05 WIB memanggil CLI di atas) tetap boleh dipasang supaya
  row tersedia tepat tengah malam, tapi **tidak wajib** — tanpa cron, row dibuat
  saat request pertama hari itu masuk. Karena query laporan memfilter berdasar
  kolom `date`, waktu row dibuat tidak memengaruhi laporan.
