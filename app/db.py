import sqlite3

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
migrate = Migrate()

# Pragma SQLite yang dijalankan pada setiap koneksi baru (aman untuk data
# yang sudah ada; journal_mode tersimpan di file DB, sisanya per-koneksi):
# - journal_mode=WAL: pembaca tidak diblokir penulis, cocok untuk multi-worker.
# - synchronous=FULL: fsync pada setiap commit — paling aman, sedikit lebih lambat.
# - foreign_keys=ON: constraint FK di-enforce di level SQLite (off secara
#   default), termasuk ON DELETE dari relasi model.
# - busy_timeout: tunggu 10 detik saat DB terkunci alih-alih langsung error.
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=FULL")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_app(app):
    db.init_app(app)
    migrate.init_app(app, db)
