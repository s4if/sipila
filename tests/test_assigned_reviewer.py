# Test penunjukan guru pereview (AssignedReviewer): form siswa,
# fragment preselect HTMX, dan materialisasi pinjaman periode.

from datetime import timedelta
from app import db
from app.helper import get_today
from app.models import (
    AssignedReviewer,
    BorrowingRequest,
    Category,
    LoanPeriod,
    Student,
)


def _selected_option(tid):
    return '<option selected value="{}">'.format(tid)


def _plain_option(tid):
    return '<option value="{}">'.format(tid)


# ---- Form tambah permintaan ----


def test_siswa_tambah_requires_reviewer(
    app, logged_in_siswa_client, kategori_with_teacher
):
    from app.helper import get_today

    response = logged_in_siswa_client.post(
        "/siswa/permintaan/tambah",
        data={
            "category_id": kategori_with_teacher.id,
            "date": get_today().isoformat(),
            "student_note": "",
        },
    )
    assert response.status_code == 200
    assert b"minimal satu guru pereview" in response.data

    with app.app_context():
        assert BorrowingRequest.query.count() == 0


def test_siswa_tambah_invalid_reviewer_rejected(
    app, logged_in_siswa_client, kategori_with_teacher
):
    from app.helper import get_today

    response = logged_in_siswa_client.post(
        "/siswa/permintaan/tambah",
        data={
            "category_id": kategori_with_teacher.id,
            "date": get_today().isoformat(),
            "student_note": "",
            "reviewers": ["99999"],
        },
    )
    assert response.status_code == 200
    assert b"Buat Permintaan" in response.data

    with app.app_context():
        assert BorrowingRequest.query.count() == 0


def test_siswa_tambah_without_category(
    app, logged_in_siswa_client, siswa_user, admin_user
):
    from app.helper import get_today

    response = logged_in_siswa_client.post(
        "/siswa/permintaan/tambah",
        data={
            "category_id": "",
            "date": get_today().isoformat(),
            "student_note": "",
            "reviewers": [str(admin_user.id)],
        },
    )
    assert response.status_code == 200
    assert b"berhasil dibuat" in response.data

    with app.app_context():
        req = BorrowingRequest.query.filter_by(
            student_id=siswa_user.id, date=get_today()
        ).one()
        assert req.category_id is None
        assert [ar.teacher_id for ar in req.assigned_reviewers] == [
            admin_user.id
        ]


def test_siswa_edit_removes_category(
    app, logged_in_siswa_client, borrowing_request, admin_user
):
    from app.helper import get_today

    response = logged_in_siswa_client.post(
        "/siswa/permintaan/edit/{}".format(borrowing_request.id),
        data={
            "category_id": "",
            "date": (get_today() + timedelta(days=1)).isoformat(),
            "student_note": "",
            "reviewers": [str(admin_user.id)],
        },
    )
    assert response.status_code == 200
    assert b"berhasil diperbarui" in response.data

    with app.app_context():
        req = db.session.get(BorrowingRequest, borrowing_request.id)
        assert req.category_id is None
        assert [ar.teacher_id for ar in req.assigned_reviewers] == [
            admin_user.id
        ]


def test_reviewer_pilihan_empty_category_no_preselect(
    logged_in_siswa_client
):
    response = logged_in_siswa_client.get(
        "/siswa/permintaan/reviewer-pilihan?category_id="
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "selected" not in html


def test_reviewer_pilihan_restores_saved_when_category_cleared(
    app, logged_in_siswa_client, siswa_user, regular_admin
):
    # permintaan tanpa kategori: mengosongkan kategori di form harus
    # mengembalikan penunjukan tersimpan (None == None)
    from app.helper import get_today

    with app.app_context():
        req = BorrowingRequest(
            student_id=siswa_user.id,
            category_id=None,
            date=get_today() + timedelta(days=1),
            status="pending",
        )
        db.session.add(req)
        db.session.flush()
        db.session.add(
            AssignedReviewer(request_id=req.id, teacher_id=regular_admin.id)
        )
        db.session.commit()
        req_id = req.id

    response = logged_in_siswa_client.get(
        "/siswa/permintaan/reviewer-pilihan?category_id=&req_id={}".format(
            req_id
        )
    )
    html = response.get_data(as_text=True)
    assert _selected_option(regular_admin.id) in html


# ---- Fragment HTMX reviewer_pilihan ----


def test_reviewer_pilihan_preselects_category_teachers(
    app, logged_in_siswa_client, kategori_with_teacher, admin_user,
    regular_admin,
):
    # admin_user = guru pengawas kategori; regular_admin bukan
    response = logged_in_siswa_client.get(
        "/siswa/permintaan/reviewer-pilihan?category_id={}".format(
            kategori_with_teacher.id
        )
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert _selected_option(admin_user.id) in html
    assert _plain_option(regular_admin.id) in html


def test_reviewer_pilihan_uses_saved_when_category_unchanged(
    app, logged_in_siswa_client, borrowing_request, kategori_with_teacher,
    admin_user, regular_admin,
):
    # permintaan tersimpan menunjuk regular_admin (bukan guru kategori);
    # bersihkan penunjukan bawaan dari fixture terlebih dahulu
    with app.app_context():
        AssignedReviewer.query.filter_by(
            request_id=borrowing_request.id
        ).delete()
        db.session.add(
            AssignedReviewer(
                request_id=borrowing_request.id,
                teacher_id=regular_admin.id,
            )
        )
        db.session.commit()

    response = logged_in_siswa_client.get(
        "/siswa/permintaan/reviewer-pilihan?category_id={}&req_id={}".format(
            kategori_with_teacher.id, borrowing_request.id
        )
    )
    html = response.get_data(as_text=True)
    # penunjukan tersimpan dipakai, bukan default kategori
    assert _selected_option(regular_admin.id) in html
    assert _plain_option(admin_user.id) in html


def test_reviewer_pilihan_ignores_other_students_request(
    app, logged_in_siswa_client, kategori_with_teacher, admin_user,
    regular_admin, siswa_user,
):
    from werkzeug.security import generate_password_hash

    with app.app_context():
        other = Student(
            student_id="S-lain",
            name="Siswa Lain",
            password=generate_password_hash("p"),
        )
        db.session.add(other)
        db.session.flush()
        req = BorrowingRequest(
            student_id=other.id,
            category_id=kategori_with_teacher.id,
            date=get_today() + timedelta(days=1),
            status="pending",
        )
        db.session.add(req)
        db.session.flush()
        db.session.add(
            AssignedReviewer(request_id=req.id, teacher_id=regular_admin.id)
        )
        db.session.commit()
        req_id = req.id

    # req milik siswa lain -> penunjukannya tidak boleh bocor,
    # kembali ke default kategori (admin_user)
    response = logged_in_siswa_client.get(
        "/siswa/permintaan/reviewer-pilihan?category_id={}&req_id={}".format(
            kategori_with_teacher.id, req_id
        )
    )
    html = response.get_data(as_text=True)
    assert _selected_option(admin_user.id) in html
    assert _plain_option(regular_admin.id) in html


def test_reviewer_pilihan_ignores_deleted_teachers(
    app, logged_in_siswa_client, kategori_with_teacher, admin_user
):
    with app.app_context():
        admin_user.is_deleted = True
        db.session.commit()

    response = logged_in_siswa_client.get(
        "/siswa/permintaan/reviewer-pilihan?category_id={}".format(
            kategori_with_teacher.id
        )
    )
    html = response.get_data(as_text=True)
    # guru yang sudah dihapus tidak muncul sebagai pilihan/preselect
    assert admin_user.username not in html
    assert 'value="{}"'.format(admin_user.id) not in html


# ---- Materialisasi pinjaman periode ----


def test_materialize_assigns_period_creator(
    app, siswa_user, kategori_with_teacher, admin_user
):
    from app.periods import materialize_periods

    with app.app_context():
        period = LoanPeriod(
            student_id=siswa_user.id,
            category_id=kategori_with_teacher.id,
            start_date=get_today(),
            end_date=get_today() + timedelta(days=1),
            created_by=admin_user.id,
        )
        db.session.add(period)
        db.session.commit()

        created = materialize_periods(get_today())
        assert created == 1

        req = BorrowingRequest.query.filter_by(
            student_id=siswa_user.id, date=get_today()
        ).one()
        # guru pemberi izin otomatis menjadi pereview
        assert [ar.teacher_id for ar in req.assigned_reviewers] == [
            admin_user.id
        ]


# ---- Detail admin menampilkan pereview ----


def test_permintaan_detail_lists_assigned_reviewers(
    logged_in_client, borrowing_request, admin_user
):
    response = logged_in_client.get(
        "/admin/permintaan/{}".format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b"Guru Pereview" in response.data
