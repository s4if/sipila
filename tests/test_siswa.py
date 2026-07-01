from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app import db
from app.models import BorrowingRequest, Student


def _make_other_student(student_id="S002"):
    other = Student(
        student_id=student_id,
        name="Siswa Lain",
        password=generate_password_hash("pass"),
    )
    db.session.add(other)
    db.session.flush()
    return other


# ---- Beranda & data permintaan ----


def test_siswa_beranda_redirects_anonymous(client):
    response = client.get("/siswa/")
    assert response.status_code == 302
    assert response.location == "/login/siswa"


def test_siswa_beranda_returns_200(logged_in_siswa_client):
    response = logged_in_siswa_client.get("/siswa/")
    assert response.status_code == 200
    assert b"Selamat Datang" in response.data


def test_siswa_permintaan_data_redirects_anonymous(client):
    response = client.get("/siswa/permintaan/data")
    assert response.status_code == 302
    assert response.location == "/login/siswa"


def test_siswa_permintaan_data_returns_json(logged_in_siswa_client):
    response = logged_in_siswa_client.get("/siswa/permintaan/data")
    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert data["data"] == []


def test_siswa_permintaan_data_includes_requests(
    app, logged_in_siswa_client, siswa_user, kategori_with_teacher
):
    with app.app_context():
        db.session.add_all(
            [
                BorrowingRequest(
                    student_id=siswa_user.id,
                    category_id=kategori_with_teacher.id,
                    date=date.today(),
                    status="pending",
                ),
                BorrowingRequest(
                    student_id=siswa_user.id,
                    category_id=kategori_with_teacher.id,
                    date=date.today() + timedelta(days=1),
                    status="accepted",
                ),
            ]
        )
        db.session.commit()

    response = logged_in_siswa_client.get("/siswa/permintaan/data")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["data"]) == 2


# ---- Tambah permintaan ----


def test_siswa_permintaan_tambah_page_get(
    logged_in_siswa_client, kategori_with_teacher
):
    response = logged_in_siswa_client.get("/siswa/permintaan/tambah")
    assert response.status_code == 200
    assert b"Buat Permintaan" in response.data


def test_siswa_permintaan_tambah_success(
    app, logged_in_siswa_client, siswa_user, kategori_with_teacher
):
    from datetime import datetime

    from app.helper import WIB

    response = logged_in_siswa_client.post(
        "/siswa/permintaan/tambah",
        data={
            "category_id": kategori_with_teacher.id,
            "date": datetime.now(WIB).date().isoformat(),
            "student_note": "catatan",
        },
    )
    assert response.status_code == 200
    assert b"berhasil dibuat" in response.data

    with app.app_context():
        req = BorrowingRequest.query.filter_by(
            student_id=siswa_user.id, date=date.today()
        ).first()
        assert req is not None
        assert req.category_id == kategori_with_teacher.id


def test_siswa_permintaan_tambah_duplicate_date(
    logged_in_siswa_client, kategori_with_teacher
):
    payload = {
        "category_id": kategori_with_teacher.id,
        "date": date.today().isoformat(),
        "student_note": "",
    }
    logged_in_siswa_client.post("/siswa/permintaan/tambah", data=payload)
    response = logged_in_siswa_client.post(
        "/siswa/permintaan/tambah", data=payload
    )
    assert response.status_code == 200
    assert b"sudah mengajukan" in response.data


def test_siswa_permintaan_tambah_outside_range(
    logged_in_siswa_client, kategori_with_teacher
):
    from datetime import datetime

    from app.helper import WIB

    yesterday = (datetime.now(WIB).date() - timedelta(days=1)).isoformat()
    response = logged_in_siswa_client.post(
        "/siswa/permintaan/tambah",
        data={
            "category_id": kategori_with_teacher.id,
            "date": yesterday,
            "student_note": "",
        },
    )
    assert response.status_code == 200
    assert b"rentang" in response.data.lower()


def test_siswa_permintaan_tambah_invalid_form(
    logged_in_siswa_client, kategori_with_teacher
):
    response = logged_in_siswa_client.post(
        "/siswa/permintaan/tambah",
        data={
            "category_id": "",
            "date": "",
            "student_note": "",
        },
    )
    assert response.status_code == 200
    assert b"Buat Permintaan" in response.data


# ---- Edit permintaan ----


def test_siswa_permintaan_edit_page_get(
    logged_in_siswa_client, borrowing_request
):
    response = logged_in_siswa_client.get(
        "/siswa/permintaan/edit/{}".format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b"Edit Permintaan" in response.data


def test_siswa_permintaan_edit_success(
    app, logged_in_siswa_client, borrowing_request, kategori_with_teacher
):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = logged_in_siswa_client.post(
        "/siswa/permintaan/edit/{}".format(borrowing_request.id),
        data={
            "category_id": kategori_with_teacher.id,
            "date": tomorrow,
            "student_note": "diubah",
        },
    )
    assert response.status_code == 200
    assert b"berhasil diperbarui" in response.data

    with app.app_context():
        req = db.session.get(BorrowingRequest, borrowing_request.id)
        assert req.date == date.today() + timedelta(days=1)
        assert req.student_note == "diubah"


def test_siswa_permintaan_edit_not_own(
    app, logged_in_siswa_client, kategori_with_teacher
):
    with app.app_context():
        other = _make_other_student()
        req = BorrowingRequest(
            student_id=other.id,
            category_id=kategori_with_teacher.id,
            date=date.today(),
            status="pending",
        )
        db.session.add(req)
        db.session.commit()
        req_id = req.id

    response = logged_in_siswa_client.get(
        "/siswa/permintaan/edit/{}".format(req_id)
    )
    assert response.status_code == 302
    assert response.location == "/siswa/"


def test_siswa_permintaan_edit_not_pending(
    app, logged_in_siswa_client, siswa_user, kategori_with_teacher
):
    with app.app_context():
        req = BorrowingRequest(
            student_id=siswa_user.id,
            category_id=kategori_with_teacher.id,
            date=date.today() + timedelta(days=2),
            status="accepted",
        )
        db.session.add(req)
        db.session.commit()
        req_id = req.id

    response = logged_in_siswa_client.get(
        "/siswa/permintaan/edit/{}".format(req_id)
    )
    assert response.status_code == 302
    assert response.location == "/siswa/"


def test_siswa_permintaan_edit_duplicate_date(
    app, logged_in_siswa_client, siswa_user, kategori_with_teacher
):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    with app.app_context():
        r1 = BorrowingRequest(
            student_id=siswa_user.id,
            category_id=kategori_with_teacher.id,
            date=today,
            status="pending",
        )
        r2 = BorrowingRequest(
            student_id=siswa_user.id,
            category_id=kategori_with_teacher.id,
            date=tomorrow,
            status="pending",
        )
        db.session.add_all([r1, r2])
        db.session.commit()
        r1_id = r1.id

    response = logged_in_siswa_client.post(
        "/siswa/permintaan/edit/{}".format(r1_id),
        data={
            "category_id": kategori_with_teacher.id,
            "date": tomorrow.isoformat(),
            "student_note": "",
        },
    )
    assert response.status_code == 200
    assert b"sudah mengajukan" in response.data


def test_siswa_permintaan_edit_404(logged_in_siswa_client):
    response = logged_in_siswa_client.get("/siswa/permintaan/edit/9999")
    assert response.status_code == 404


# ---- Batal permintaan ----


def test_siswa_permintaan_batal_success(
    app, logged_in_siswa_client, borrowing_request
):
    response = logged_in_siswa_client.post(
        "/siswa/permintaan/batal", data={"id": borrowing_request.id}
    )
    assert response.status_code == 200
    assert b"berhasil dibatalkan" in response.data

    with app.app_context():
        assert db.session.get(BorrowingRequest, borrowing_request.id) is None


def test_siswa_permintaan_batal_not_own(
    app, logged_in_siswa_client, kategori_with_teacher
):
    with app.app_context():
        other = _make_other_student()
        req = BorrowingRequest(
            student_id=other.id,
            category_id=kategori_with_teacher.id,
            date=date.today(),
            status="pending",
        )
        db.session.add(req)
        db.session.commit()
        req_id = req.id

    response = logged_in_siswa_client.post(
        "/siswa/permintaan/batal", data={"id": req_id}
    )
    assert response.status_code == 200
    assert b"tidak berwenang" in response.data


def test_siswa_permintaan_batal_not_pending(
    app, logged_in_siswa_client, siswa_user, kategori_with_teacher
):
    with app.app_context():
        req = BorrowingRequest(
            student_id=siswa_user.id,
            category_id=kategori_with_teacher.id,
            date=date.today() + timedelta(days=3),
            status="accepted",
        )
        db.session.add(req)
        db.session.commit()
        req_id = req.id

    response = logged_in_siswa_client.post(
        "/siswa/permintaan/batal", data={"id": req_id}
    )
    assert response.status_code == 200
    assert b"pending" in response.data.lower()


def test_siswa_permintaan_batal_404(logged_in_siswa_client):
    response = logged_in_siswa_client.post(
        "/siswa/permintaan/batal", data={"id": 9999}
    )
    assert response.status_code == 404


# ---- Detail permintaan ----


def test_siswa_permintaan_detail_page(
    logged_in_siswa_client, borrowing_request
):
    response = logged_in_siswa_client.get(
        "/siswa/permintaan/{}".format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b"Detail Permintaan" in response.data


def test_siswa_permintaan_detail_not_own(
    app, logged_in_siswa_client, kategori_with_teacher
):
    with app.app_context():
        other = _make_other_student()
        req = BorrowingRequest(
            student_id=other.id,
            category_id=kategori_with_teacher.id,
            date=date.today(),
            status="pending",
        )
        db.session.add(req)
        db.session.commit()
        req_id = req.id

    response = logged_in_siswa_client.get("/siswa/permintaan/{}".format(req_id))
    assert response.status_code == 302
    assert response.location == "/siswa/"


def test_siswa_permintaan_detail_404(logged_in_siswa_client):
    response = logged_in_siswa_client.get("/siswa/permintaan/9999")
    assert response.status_code == 404


# ---- Logout siswa ----


def test_siswa_logout(logged_in_siswa_client):
    response = logged_in_siswa_client.get("/siswa/logout")
    assert response.status_code == 302
    assert response.location == "/login/siswa"
    with logged_in_siswa_client.session_transaction() as sess:
        assert "student_id" not in sess
        assert "logged_in" not in sess
