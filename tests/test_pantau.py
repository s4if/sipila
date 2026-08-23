from datetime import date, timedelta
from itertools import count

from werkzeug.security import generate_password_hash

from app import db
from app.models import BorrowingRequest, Category, ClassGroup, Student


_setup_seq = count()


def _setup_borrowing_request(
    app, status="pending", tanggal=None, nama="Siswa Pantau"
):
    with app.app_context():
        n = next(_setup_seq)
        cg = ClassGroup(name="1", grade_level="X", major="TJKT")
        db.session.add(cg)
        db.session.flush()

        student = Student(
            student_id="P{:03d}".format(n + 1),
            name=nama,
            password=generate_password_hash("pass"),
            class_group_id=cg.id,
        )
        db.session.add(student)
        db.session.flush()

        cat = Category(name="Kategori Pantau {}".format(n))
        db.session.add(cat)
        db.session.flush()

        req = BorrowingRequest(
            student_id=student.id,
            category_id=cat.id,
            date=tanggal if tanggal else date.today(),
            status=status,
        )
        db.session.add(req)
        db.session.commit()

        return req.id


def test_monitor_publik_page_public(client):
    # Halaman bisa diakses tanpa login
    response = client.get("/pantau")
    assert response.status_code == 200
    assert b"Permintaan Peminjaman Hari Ini" in response.data


def test_monitor_publik_data_public(client):
    response = client.get("/pantau/data")
    assert response.status_code == 200
    data = response.get_json()
    assert data == {"data": []}


def test_monitor_publik_data_shows_all_statuses(client, app):
    _setup_borrowing_request(app, status="pending", nama="Siswa Pending")
    _setup_borrowing_request(app, status="accepted", nama="Siswa Diterima")
    _setup_borrowing_request(app, status="rejected", nama="Siswa Ditolak")

    response = client.get("/pantau/data")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert len(data) == 3

    nama_status = {row["student_name"]: row["status"] for row in data}
    assert "Pending" in nama_status["Siswa Pending"]
    assert "Diterima" in nama_status["Siswa Diterima"]
    assert "Ditolak" in nama_status["Siswa Ditolak"]


def test_monitor_publik_data_columns(client, app):
    _setup_borrowing_request(app, nama="Siswa Kolom")

    response = client.get("/pantau/data")
    row = response.get_json()["data"][0]
    assert set(row.keys()) == {
        "student_name",
        "class_group",
        "category",
        "status",
    }
    assert row["student_name"] == "Siswa Kolom"
    assert row["class_group"] == "X TJKT 1"
    assert row["category"].startswith("Kategori Pantau")


def test_monitor_publik_data_only_today(client, app):
    # Permintaan kemarin dan besok tidak boleh muncul
    _setup_borrowing_request(
        app, tanggal=date.today() - timedelta(days=1), nama="Siswa Kemarin"
    )
    _setup_borrowing_request(
        app, tanggal=date.today() + timedelta(days=1), nama="Siswa Besok"
    )
    _setup_borrowing_request(app, nama="Siswa Hari Ini")

    response = client.get("/pantau/data")
    data = response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["student_name"] == "Siswa Hari Ini"
