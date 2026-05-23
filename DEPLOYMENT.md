# Catatan Deployment

## Timezone Database (UTC)

Database **harus** dikonfigurasi dengan timezone **UTC** untuk memastikan konsistensi waktu di seluruh aplikasi.

Aplikasi menggunakan konstanta `WIB (UTC+7)` di `app/helper.py` sebagai satu-satunya acuan waktu untuk semua operasi bisnis (rentang tanggal peminjaman, pembatalan keputusan, dll). Field `created_at` pada model juga disimpan dalam UTC.

### SQLite (Development)

Secara default SQLite tidak memiliki konsep timezone, jadi tidak perlu konfigurasi tambahan. Pastikan server menjalankan `date.today()` tidak digunakan langsung — selalu gunakan `datetime.now(WIB).date()`.

### PostgreSQL (Production)

```sql
-- Verifikasi timezone database
SHOW timezone;

-- Set ke UTC jika belum
ALTER DATABASE sipila SET timezone TO 'UTC';
```

### Docker

Pastikan container juga berjalan dengan timezone UTC (default Docker). **Jangan** set `TZ` environment variable ke `Asia/Jakarta` di container, karena aplikasi sudah menangani konversi waktu secara manual menggunakan konstanta `WIB`.

```yaml
# docker-compose.yml — JANGAN tambahkan ini:
# environment:
#   - TZ=Asia/Jakarta    # <-- TIDAK PERLU, hapus jika ada
```
