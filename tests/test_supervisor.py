from datetime import date, datetime, timezone

from app import db
from app.models import (
    BorrowingRequest,
    Category,
    ClassGroup,
    Student,
    Teacher,
)
from werkzeug.security import generate_password_hash


def _setup_borrowing_request(app, status="accepted", confirmation=None):
    with app.app_context():
        teacher = Teacher(
            username="guru_review",
            password=generate_password_hash("pass"),
            name="Guru Review",
        )
        db.session.add(teacher)
        db.session.flush()

        cg = ClassGroup(name="1", grade_level="X", major="TJKT")
        db.session.add(cg)
        db.session.flush()

        student = Student(
            student_id="S001",
            name="Siswa Satu",
            password=generate_password_hash("pass"),
            class_group_id=cg.id,
        )
        db.session.add(student)
        db.session.flush()

        cat = Category(name="Laptop")
        db.session.add(cat)
        db.session.flush()

        req = BorrowingRequest(
            student_id=student.id,
            category_id=cat.id,
            date=date.today(),
            status=status,
            reviewed_by=teacher.id,
            reviewed_at=datetime.now(timezone.utc),
            confirmation=confirmation,
        )
        if confirmation:
            req.confirmed_by = teacher.id
            req.confirmed_at = datetime.now(timezone.utc)
        db.session.add(req)
        db.session.commit()

        return req.id


def test_monitor_page_returns_200(logged_in_client):
    response = logged_in_client.get("/supervisor/monitor")
    assert response.status_code == 200
    assert b"Monitor Peminjaman" in response.data


def test_monitor_page_redirects_anonymous(client):
    response = client.get("/supervisor/monitor")
    assert response.status_code == 302
    assert "login" in response.location


def test_monitor_data_returns_json(logged_in_client, app):
    _setup_borrowing_request(app)
    response = logged_in_client.get("/supervisor/monitor/data")
    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["confirmation"] is None


def test_monitor_data_includes_confirmation_used(logged_in_client, app):
    _setup_borrowing_request(app, confirmation="used")
    response = logged_in_client.get("/supervisor/monitor/data")
    data = response.get_json()
    assert data["data"][0]["confirmation"] == "used"


def test_monitor_data_includes_confirmation_not_used(logged_in_client, app):
    _setup_borrowing_request(app, confirmation="not_used")
    response = logged_in_client.get("/supervisor/monitor/data")
    data = response.get_json()
    assert data["data"][0]["confirmation"] == "not_used"


def test_monitor_konfirmasi_used(logged_in_client, app):
    req_id = _setup_borrowing_request(app)
    response = logged_in_client.post(
        "/supervisor/monitor/konfirmasi/{}".format(req_id),
        data={"confirmation": "used"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "digunakan" in data["message"]

    with app.app_context():
        req = db.session.get(BorrowingRequest, req_id)
        assert req.confirmation == "used"
        assert req.confirmed_by is not None
        assert req.confirmed_at is not None


def test_monitor_konfirmasi_not_used(logged_in_client, app):
    req_id = _setup_borrowing_request(app)
    response = logged_in_client.post(
        "/supervisor/monitor/konfirmasi/{}".format(req_id),
        data={"confirmation": "not_used"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "tidak digunakan" in data["message"]

    with app.app_context():
        req = db.session.get(BorrowingRequest, req_id)
        assert req.confirmation == "not_used"


def test_monitor_konfirmasi_invalid_value(logged_in_client, app):
    req_id = _setup_borrowing_request(app)
    response = logged_in_client.post(
        "/supervisor/monitor/konfirmasi/{}".format(req_id),
        data={"confirmation": "invalid"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_monitor_konfirmasi_rejected_request_fails(logged_in_client, app):
    req_id = _setup_borrowing_request(app, status="rejected")
    response = logged_in_client.post(
        "/supervisor/monitor/konfirmasi/{}".format(req_id),
        data={"confirmation": "used"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_monitor_konfirmasi_pending_request_fails(logged_in_client, app):
    req_id = _setup_borrowing_request(app, status="pending")
    response = logged_in_client.post(
        "/supervisor/monitor/konfirmasi/{}".format(req_id),
        data={"confirmation": "used"},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_monitor_konfirmasi_404(logged_in_client):
    response = logged_in_client.post(
        "/supervisor/monitor/konfirmasi/9999",
        data={"confirmation": "used"},
    )
    assert response.status_code == 404


def test_monitor_konfirmasi_requires_login(client):
    response = client.post(
        "/supervisor/monitor/konfirmasi/1",
        data={"confirmation": "used"},
    )
    assert response.status_code == 302
    assert "login" in response.location


def test_monitor_batalkan_konfirmasi(logged_in_client, app):
    req_id = _setup_borrowing_request(app, confirmation="used")
    response = logged_in_client.post(
        "/supervisor/monitor/batalkan_konfirmasi/{}".format(req_id),
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "dibatalkan" in data["message"]

    with app.app_context():
        req = db.session.get(BorrowingRequest, req_id)
        assert req.confirmation is None
        assert req.confirmed_by is None
        assert req.confirmed_at is None


def test_monitor_batalkan_unconfirmed_fails(logged_in_client, app):
    req_id = _setup_borrowing_request(app)
    response = logged_in_client.post(
        "/supervisor/monitor/batalkan_konfirmasi/{}".format(req_id),
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_monitor_batalkan_rejected_request_fails(logged_in_client, app):
    req_id = _setup_borrowing_request(app, status="rejected", confirmation="used")
    response = logged_in_client.post(
        "/supervisor/monitor/batalkan_konfirmasi/{}".format(req_id),
    )
    assert response.status_code == 400


def test_monitor_batalkan_404(logged_in_client):
    response = logged_in_client.post(
        "/supervisor/monitor/batalkan_konfirmasi/9999",
    )
    assert response.status_code == 404


def test_monitor_batalkan_requires_login(client):
    response = client.post("/supervisor/monitor/batalkan_konfirmasi/1")
    assert response.status_code == 302
    assert "login" in response.location


def test_monitor_konfirmasi_reversible(logged_in_client, app):
    req_id = _setup_borrowing_request(app)

    logged_in_client.post(
        "/supervisor/monitor/konfirmasi/{}".format(req_id),
        data={"confirmation": "used"},
    )
    with app.app_context():
        req = db.session.get(BorrowingRequest, req_id)
        assert req.confirmation == "used"

    logged_in_client.post(
        "/supervisor/monitor/batalkan_konfirmasi/{}".format(req_id),
    )
    with app.app_context():
        req = db.session.get(BorrowingRequest, req_id)
        assert req.confirmation is None

    logged_in_client.post(
        "/supervisor/monitor/konfirmasi/{}".format(req_id),
        data={"confirmation": "not_used"},
    )
    with app.app_context():
        req = db.session.get(BorrowingRequest, req_id)
        assert req.confirmation == "not_used"
