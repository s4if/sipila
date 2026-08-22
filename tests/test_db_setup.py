"""Tes konfigurasi SQLite: WAL, synchronous=FULL, busy_timeout, dan pool
yang aman untuk gunicorn + gevent."""


def test_file_sqlite_menggunakan_wal(tmp_path):
    from app import create_app, db

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/wal_test.db",
            "WTF_CSRF_ENABLED": False,
            "LOGIN_CAPTCHA_ENABLED": False,
            "SECRET_KEY": "test",
        }
    )
    with app.app_context():
        db.create_all()
        with db.engine.connect() as conn:
            assert conn.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
            # synchronous: 1 = NORMAL, 2 = FULL
            assert conn.exec_driver_sql("PRAGMA synchronous").scalar() == 2
            assert conn.exec_driver_sql("PRAGMA busy_timeout").scalar() == 10000


def test_file_sqlite_menggunakan_nullpool(tmp_path):
    from sqlalchemy.pool import NullPool

    from app import create_app, db

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/pool_test.db",
            "WTF_CSRF_ENABLED": False,
            "LOGIN_CAPTCHA_ENABLED": False,
            "SECRET_KEY": "test",
        }
    )
    with app.app_context():
        db.create_all()
        assert isinstance(db.engine.pool, NullPool)


def test_memory_db_tetap_staticpool(app):
    # Fixture `app` memakai sqlite:///:memory: — Flask-SQLAlchemy memaksa
    # StaticPool untuk itu, jadi opsi NullPool tidak boleh merusak testing.
    from sqlalchemy.pool import StaticPool

    from app import db

    with app.app_context():
        assert isinstance(db.engine.pool, StaticPool)
