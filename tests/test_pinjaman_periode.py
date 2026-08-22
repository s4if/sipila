from datetime import timedelta

from app import db
from app.helper import get_today
from app.models import BorrowingRequest, Category, CategoryTeacher, LoanPeriod


def _make_period(student, category, teacher, start=None, end=None, **kwargs):
    today = get_today()
    period = LoanPeriod(
        student_id=student.id,
        category_id=category.id,
        start_date=start or today,
        end_date=end or today + timedelta(days=3),
        created_by=teacher.id,
        **kwargs,
    )
    db.session.add(period)
    db.session.commit()
    return period


def _count_requests(student_id):
    return BorrowingRequest.query.filter_by(student_id=student_id).count()


# ---- Model ----


def test_loan_period_repr_and_status_label(app, siswa_user, kategori_with_teacher, admin_user):
    today = get_today()
    period = _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=2),
    )
    assert "LoanPeriod" in repr(period)
    assert period.status_label == "active"

    future = _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today + timedelta(days=5),
        end=today + timedelta(days=7),
    )
    assert future.status_label == "upcoming"

    past = _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today - timedelta(days=5),
        end=today - timedelta(days=1),
    )
    assert past.status_label == "concluded"

    period.is_active = False
    db.session.commit()
    assert period.status_label == "cancelled"


# ---- materialize_periods ----


def test_materialize_creates_accepted_request_for_today(
    app, siswa_user, kategori_with_teacher, admin_user
):
    from app.periods import materialize_periods

    today = get_today()
    period = _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=2),
    )

    created = materialize_periods(today)
    assert created == 1
    req = BorrowingRequest.query.filter_by(
        student_id=siswa_user.id, date=today
    ).one()
    assert req.status == "accepted"
    assert req.loan_period_id == period.id
    assert req.reviewed_by == admin_user.id
    assert req.category_id == kategori_with_teacher.id


def test_materialize_skips_date_outside_range(
    app, siswa_user, kategori_with_teacher, admin_user
):
    from app.periods import materialize_periods

    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today + timedelta(days=2),
        end=today + timedelta(days=5),
    )

    created = materialize_periods(today)
    assert created == 0
    assert _count_requests(siswa_user.id) == 0

    created = materialize_periods(today + timedelta(days=3))
    assert created == 1


def test_materialize_skips_banned_student(
    app, siswa_user, kategori_with_teacher, admin_user, student_ban
):
    from app.periods import materialize_periods

    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=2),
    )

    created = materialize_periods(today)
    assert created == 0
    assert _count_requests(siswa_user.id) == 0


def test_materialize_idempotent(
    app, siswa_user, kategori_with_teacher, admin_user
):
    from app.periods import materialize_periods

    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=2),
    )

    assert materialize_periods(today) == 1
    assert materialize_periods(today) == 0
    assert _count_requests(siswa_user.id) == 1


def test_materialize_keeps_existing_manual_request(
    app, siswa_user, kategori_with_teacher, admin_user, borrowing_request
):
    from app.periods import materialize_periods

    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=2),
    )

    created = materialize_periods(today)
    assert created == 0
    req = BorrowingRequest.query.filter_by(
        student_id=siswa_user.id, date=today
    ).one()
    # Permintaan manual siswa tidak ditimpa
    assert req.status == "pending"
    assert req.loan_period_id is None


def test_materialize_skips_deleted_student(
    app, siswa_user, kategori_with_teacher, admin_user
):
    from app.periods import materialize_periods

    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=2),
    )
    siswa_user.is_deleted = True
    db.session.commit()

    assert materialize_periods(today) == 0


def test_materialize_skips_inactive_period(
    app, siswa_user, kategori_with_teacher, admin_user
):
    from app.periods import materialize_periods

    today = get_today()
    period = _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=2),
    )
    period.is_active = False
    db.session.commit()

    assert materialize_periods(today) == 0


# ---- CLI materialize-periods ----


def test_cli_materialize_creates_for_today(
    app, runner, siswa_user, kategori_with_teacher, admin_user
):
    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=1),
    )

    result = runner.invoke(args=["materialize-periods"])
    assert result.exit_code == 0
    assert "1" in result.output
    assert _count_requests(siswa_user.id) == 1


def test_cli_materialize_with_explicit_date(
    app, runner, siswa_user, kategori_with_teacher, admin_user
):
    today = get_today()
    target = today + timedelta(days=2)
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=3),
    )

    result = runner.invoke(
        args=["materialize-periods", "--date", target.isoformat()]
    )
    assert result.exit_code == 0
    req = BorrowingRequest.query.filter_by(
        student_id=siswa_user.id, date=target
    ).one()
    assert req.status == "accepted"


def test_cli_materialize_invalid_date(app, runner):
    result = runner.invoke(args=["materialize-periods", "--date", "bogus"])
    assert result.exit_code != 0
    assert "YYYY-MM-DD" in result.output


# ---- Route: tambah pinjaman periode ----


def test_tambah_form_shows_all_categories_for_superadmin(
    logged_in_client, siswa_user, kategori_with_teacher
):
    other = Category(name="Lainnya")
    db.session.add(other)
    db.session.commit()

    response = logged_in_client.get(
        "/admin/siswa/{}/pinjaman-periode/tambah".format(siswa_user.id)
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Kategori Test" in html
    assert "Lainnya" in html


def test_tambah_form_limits_categories_for_regular_admin(
    app, regular_admin_client, regular_admin, siswa_user, kategori_with_teacher
):
    cat = Category(name="Milik Guru")
    db.session.add(cat)
    db.session.flush()
    db.session.add(
        CategoryTeacher(category_id=cat.id, teacher_id=regular_admin.id)
    )
    db.session.commit()

    response = regular_admin_client.get(
        "/admin/siswa/{}/pinjaman-periode/tambah".format(siswa_user.id)
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Milik Guru" in html
    assert "Kategori Test" not in html


def test_tambah_creates_period_and_materializes_today(
    logged_in_client, siswa_user, kategori_with_teacher
):
    today = get_today()
    data = {
        "category_id": kategori_with_teacher.id,
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=2)).isoformat(),
        "note": "Lomba robotik",
    }
    response = logged_in_client.post(
        "/admin/siswa/{}/pinjaman-periode/tambah".format(siswa_user.id),
        data=data,
    )
    assert response.status_code == 200

    period = LoanPeriod.query.filter_by(student_id=siswa_user.id).one()
    assert period.is_active is True
    assert period.note == "Lomba robotik"

    # Row hari ini langsung dibuat karena rentang mencakup hari ini
    req = BorrowingRequest.query.filter_by(
        student_id=siswa_user.id, date=today
    ).one()
    assert req.loan_period_id == period.id


def test_tambah_future_period_does_not_materialize_today(
    logged_in_client, siswa_user, kategori_with_teacher
):
    today = get_today()
    data = {
        "category_id": kategori_with_teacher.id,
        "start_date": (today + timedelta(days=3)).isoformat(),
        "end_date": (today + timedelta(days=5)).isoformat(),
    }
    response = logged_in_client.post(
        "/admin/siswa/{}/pinjaman-periode/tambah".format(siswa_user.id),
        data=data,
    )
    assert response.status_code == 200
    assert _count_requests(siswa_user.id) == 0


def test_tambah_rejects_inverted_range(
    logged_in_client, siswa_user, kategori_with_teacher
):
    today = get_today()
    data = {
        "category_id": kategori_with_teacher.id,
        "start_date": (today + timedelta(days=5)).isoformat(),
        "end_date": today.isoformat(),
    }
    response = logged_in_client.post(
        "/admin/siswa/{}/pinjaman-periode/tambah".format(siswa_user.id),
        data=data,
    )
    html = response.get_data(as_text=True)
    assert "Tanggal mulai tidak boleh lebih besar" in html
    assert LoanPeriod.query.count() == 0


def test_tambah_rejects_past_start_date(
    logged_in_client, siswa_user, kategori_with_teacher
):
    today = get_today()
    data = {
        "category_id": kategori_with_teacher.id,
        "start_date": (today - timedelta(days=1)).isoformat(),
        "end_date": (today + timedelta(days=2)).isoformat(),
    }
    response = logged_in_client.post(
        "/admin/siswa/{}/pinjaman-periode/tambah".format(siswa_user.id),
        data=data,
    )
    html = response.get_data(as_text=True)
    assert "masa lalu" in html
    assert LoanPeriod.query.count() == 0


def test_tambah_rejects_overlapping_period(
    logged_in_client, siswa_user, kategori_with_teacher, admin_user
):
    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today + timedelta(days=5),
        end=today + timedelta(days=10),
    )
    data = {
        "category_id": kategori_with_teacher.id,
        "start_date": (today + timedelta(days=8)).isoformat(),
        "end_date": (today + timedelta(days=12)).isoformat(),
    }
    response = logged_in_client.post(
        "/admin/siswa/{}/pinjaman-periode/tambah".format(siswa_user.id),
        data=data,
    )
    html = response.get_data(as_text=True)
    assert "beririsan" in html
    assert LoanPeriod.query.count() == 1


def test_tambah_regular_admin_cannot_use_foreign_category(
    app, regular_admin_client, regular_admin, siswa_user, kategori_with_teacher
):
    today = get_today()
    data = {
        "category_id": kategori_with_teacher.id,  # kategori milik superadmin
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=2)).isoformat(),
    }
    response = regular_admin_client.post(
        "/admin/siswa/{}/pinjaman-periode/tambah".format(siswa_user.id),
        data=data,
    )
    assert response.status_code == 200
    assert LoanPeriod.query.count() == 0


# ---- Route: batalkan pinjaman periode ----


def test_permintaan_detail_shows_loan_period_info(
    logged_in_client, siswa_user, kategori_with_teacher, admin_user
):
    from app.periods import materialize_periods

    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=2),
    )
    materialize_periods(today)
    req = BorrowingRequest.query.filter_by(
        student_id=siswa_user.id, date=today
    ).one()

    response = logged_in_client.get("/admin/permintaan/{}".format(req.id))
    assert response.status_code == 200
    assert "Bagian dari pinjaman periode" in response.get_data(as_text=True)


def test_batalkan_by_creator(
    app, regular_admin_client, siswa_user, kategori_with_teacher, regular_admin
):
    period = _make_period(siswa_user, kategori_with_teacher, regular_admin)
    response = regular_admin_client.post(
        "/admin/pinjaman-periode/batalkan/{}".format(period.id)
    )
    assert response.status_code == 200
    assert period.is_active is False
    assert period.cancelled_at is not None


def test_batalkan_by_superadmin(
    logged_in_client, siswa_user, kategori_with_teacher, admin_user
):
    period = _make_period(siswa_user, kategori_with_teacher, admin_user)
    response = logged_in_client.post(
        "/admin/pinjaman-periode/batalkan/{}".format(period.id)
    )
    assert response.status_code == 200
    assert period.is_active is False


def test_batalkan_rejected_for_other_regular_admin(
    app,
    regular_admin_client,
    siswa_user,
    kategori_with_teacher,
    admin_user,
):
    # Periode dibuat superadmin, dibatalkan guru lain (bukan superadmin)
    period = _make_period(siswa_user, kategori_with_teacher, admin_user)
    response = regular_admin_client.post(
        "/admin/pinjaman-periode/batalkan/{}".format(period.id)
    )
    html = response.get_data(as_text=True)
    assert "tidak berwenang" in html
    assert period.is_active is True


def test_batalkan_twice_fails(
    logged_in_client, siswa_user, kategori_with_teacher, admin_user
):
    period = _make_period(siswa_user, kategori_with_teacher, admin_user)
    period.is_active = False
    db.session.commit()

    response = logged_in_client.post(
        "/admin/pinjaman-periode/batalkan/{}".format(period.id)
    )
    html = response.get_data(as_text=True)
    assert "sudah tidak aktif" in html


# ---- Siswa: tidak bisa mengajukan manual di tanggal tercakup periode ----


def test_siswa_manual_request_blocked_within_period(
    app, logged_in_siswa_client, siswa_user, kategori_with_teacher, admin_user
):
    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today,
        end=today + timedelta(days=5),
    )

    data = {
        "category_id": kategori_with_teacher.id,
        "date": (today + timedelta(days=1)).isoformat(),
        "student_note": "coba ajukan manual",
    }
    response = logged_in_siswa_client.post("/siswa/permintaan/tambah", data=data)
    html = response.get_data(as_text=True)
    assert "pinjaman periode" in html
    assert _count_requests(siswa_user.id) == 0


def test_siswa_manual_request_allowed_outside_period(
    app, logged_in_siswa_client, siswa_user, kategori_with_teacher, admin_user
):
    today = get_today()
    _make_period(
        siswa_user,
        kategori_with_teacher,
        admin_user,
        start=today + timedelta(days=3),
        end=today + timedelta(days=5),
    )

    data = {
        "category_id": kategori_with_teacher.id,
        "date": (today + timedelta(days=1)).isoformat(),
    }
    response = logged_in_siswa_client.post("/siswa/permintaan/tambah", data=data)
    html = response.get_data(as_text=True)
    assert "berhasil dibuat" in html
    assert _count_requests(siswa_user.id) == 1
