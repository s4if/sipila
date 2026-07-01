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
