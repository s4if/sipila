import pytest

from app import create_app, db


def test_get_login_page(client):
    response = client.get("/login/admin")
    assert response.status_code == 200
    assert (
        b"Login" in response.data
        or b"login" in response.data
        or b"Username" in response.data
    )


def test_login_valid_credentials(client, admin_user):
    response = client.post(
        "/login/admin",
        data={
            "username": "admin",
            "password": "secret",
        },
    )
    assert response.status_code == 302
    assert response.location == "/admin/"


def test_login_wrong_password(client, admin_user):
    response = client.post(
        "/login/admin",
        data={
            "username": "admin",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 200
    assert (
        b"tidak sesuai" in response.data.lower()
        or b"invalid" in response.data.lower()
        or b"salah" in response.data
    )


def test_login_deleted_teacher(client, app, admin_user):
    from app import db

    with app.app_context():
        admin_user.is_deleted = True
        db.session.commit()

    response = client.post(
        "/login/admin",
        data={
            "username": "admin",
            "password": "secret",
        },
    )
    assert response.status_code == 200
    assert (
        b"invalid" in response.data.lower()
        or b"salah" in response.data.lower()
    )


def test_login_nonexistent_user(client):
    response = client.post(
        "/login/admin",
        data={
            "username": "nobody",
            "password": "secret",
        },
    )
    assert response.status_code == 200
    assert (
        b"tidak sesuai" in response.data.lower()
        or b"invalid" in response.data.lower()
        or b"salah" in response.data
        or b"not found" in response.data
    )


def test_logout(client):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["is_admin"] = True
        sess["is_superadmin"] = True
        sess["admin_name"] = "admin"
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.location == "/login/admin"
    with client.session_transaction() as sess:
        assert "logged_in" not in sess
        assert "is_admin" not in sess


# ---- Siswa login tests ----


def test_get_siswa_login_page(client):
    response = client.get("/login/siswa")
    assert response.status_code == 200
    assert b"Login Siswa" in response.data


def test_siswa_login_valid_credentials(client, siswa_user):
    response = client.post(
        "/login/siswa",
        data={
            "student_id": "S001",
            "password": "rahasia",
        },
    )
    assert response.status_code == 302
    assert response.location == "/siswa/"


def test_siswa_login_wrong_password(client, siswa_user):
    response = client.post(
        "/login/siswa",
        data={
            "student_id": "S001",
            "password": "salah",
        },
    )
    assert response.status_code == 200
    assert b"salah" in response.data.lower()


def test_siswa_login_nonexistent_nis(client):
    response = client.post(
        "/login/siswa",
        data={
            "student_id": "TIDAKADA",
            "password": "rahasia",
        },
    )
    assert response.status_code == 200
    assert b"salah" in response.data.lower()


def test_siswa_login_deleted_student(client, app, siswa_user):
    from app import db

    with app.app_context():
        siswa_user.is_deleted = True
        db.session.commit()

    response = client.post(
        "/login/siswa",
        data={
            "student_id": "S001",
            "password": "rahasia",
        },
    )
    assert response.status_code == 200
    assert b"salah" in response.data.lower()


# ---- Captcha tests ----
# Captcha defaultnya aktif di production. Fixture `app` (di atas) sengaja
# mematikannya supaya test kredensial diisolasi. Di sini kita bikin app
# terpisah dengan captcha menyala untuk menguji perilakunya.


@pytest.fixture
def captcha_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "LOGIN_CAPTCHA_ENABLED": True,
            "SECRET_KEY": "test",
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def captcha_client(captcha_app):
    return captcha_app.test_client()


@pytest.fixture
def captcha_admin(captcha_app):
    from werkzeug.security import generate_password_hash

    from app.models import Teacher

    with captcha_app.app_context():
        user = Teacher(
            username="admin",
            password=generate_password_hash("secret"),
            is_superadmin=True,
        )
        db.session.add(user)
        db.session.commit()
        return user


def test_admin_login_page_shows_captcha_image(captcha_client):
    response = captcha_client.get("/login/admin")
    assert response.status_code == 200
    assert b"data:image/png;base64," in response.data


def test_siswa_login_page_shows_captcha_image(captcha_client):
    response = captcha_client.get("/login/siswa")
    assert response.status_code == 200
    assert b"data:image/png;base64," in response.data


def test_login_blocked_when_captcha_wrong(captcha_client, captcha_admin):
    from app.helper import captcha_hash

    with captcha_client.session_transaction() as sess:
        sess["captcha_answer"] = captcha_hash("ZZZZZ")
    response = captcha_client.post(
        "/login/admin",
        data={"username": "admin", "password": "secret", "captcha": "ABCDE"},
    )
    assert response.status_code == 200
    assert b"keamanan salah" in response.data.lower()
    with captcha_client.session_transaction() as sess:
        assert "logged_in" not in sess


def test_login_blocked_when_captcha_missing(captcha_client, captcha_admin):
    response = captcha_client.post(
        "/login/admin",
        data={"username": "admin", "password": "secret"},
    )
    assert response.status_code == 200
    assert b"keamanan salah" in response.data.lower()


def test_login_succeeds_with_correct_captcha(captcha_client, captcha_admin):
    from app.helper import captcha_hash

    with captcha_client.session_transaction() as sess:
        sess["captcha_answer"] = captcha_hash("WXB3K")
    response = captcha_client.post(
        "/login/admin",
        data={"username": "admin", "password": "secret", "captcha": "wxb3k"},
    )
    assert response.status_code == 302
    assert response.location == "/admin/"


def test_captcha_endpoint_returns_base64_image(captcha_client):
    response = captcha_client.get("/login/captcha")
    assert response.status_code == 200
    assert b"data:image/png;base64," in response.data
    with captcha_client.session_transaction() as sess:
        assert "captcha_answer" in sess
