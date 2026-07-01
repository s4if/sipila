from datetime import date, timedelta

from app import db
from app.models import BorrowingRequest, Category, CategoryTeacher


def _make_request(student_id, category_id, status='pending', offset_days=1,
                  reviewed_by=None):
    req = BorrowingRequest(
        student_id=student_id,
        category_id=category_id,
        date=date.today() + timedelta(days=offset_days),
        status=status,
        reviewed_by=reviewed_by,
    )
    db.session.add(req)
    db.session.flush()
    return req


# ---- Data & detail ----


def test_permintaan_data_returns_json(logged_in_client):
    response = logged_in_client.get('/admin/permintaan/data')
    assert response.status_code == 200
    data = response.get_json()
    assert 'data' in data


def test_permintaan_data_filters_by_teacher_category(
    app, regular_admin_client, regular_admin, siswa_user
):
    with app.app_context():
        cat_a = Category(name='A')
        cat_b = Category(name='B')
        db.session.add_all([cat_a, cat_b])
        db.session.flush()
        db.session.add(CategoryTeacher(
            category_id=cat_a.id, teacher_id=regular_admin.id
        ))
        db.session.flush()
        db.session.add_all([
            BorrowingRequest(
                student_id=siswa_user.id, category_id=cat_a.id,
                date=date.today(), status='pending',
            ),
            BorrowingRequest(
                student_id=siswa_user.id, category_id=cat_b.id,
                date=date.today() + timedelta(days=1), status='pending',
            ),
        ])
        db.session.commit()

    response = regular_admin_client.get('/admin/permintaan/data')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['data']) == 1
    assert data['data'][0]['category'] == 'A'


def test_permintaan_data_superadmin_sees_all(app, logged_in_client, siswa_user):
    with app.app_context():
        cat_a = Category(name='A')
        cat_b = Category(name='B')
        db.session.add_all([cat_a, cat_b])
        db.session.flush()
        db.session.add_all([
            BorrowingRequest(
                student_id=siswa_user.id, category_id=cat_a.id,
                date=date.today(), status='pending',
            ),
            BorrowingRequest(
                student_id=siswa_user.id, category_id=cat_b.id,
                date=date.today() + timedelta(days=1), status='pending',
            ),
        ])
        db.session.commit()

    response = logged_in_client.get('/admin/permintaan/data')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['data']) == 2


def test_permintaan_detail_page(logged_in_client, borrowing_request):
    response = logged_in_client.get(
        '/admin/permintaan/{}'.format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b'Detail Permintaan' in response.data


def test_permintaan_detail_can_review(logged_in_client, borrowing_request):
    response = logged_in_client.get(
        '/admin/permintaan/{}'.format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b'Tinjau Permintaan' in response.data


def test_permintaan_detail_cannot_review(
    regular_admin_client, borrowing_request
):
    response = regular_admin_client.get(
        '/admin/permintaan/{}'.format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b'Tinjau Permintaan' not in response.data


def test_permintaan_detail_404(logged_in_client):
    response = logged_in_client.get('/admin/permintaan/9999')
    assert response.status_code == 404


# ---- Terima ----


def test_permintaan_terima_success(
    app, logged_in_client, admin_user, borrowing_request
):
    response = logged_in_client.post(
        '/admin/permintaan/terima/{}'.format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b'berhasil diterima' in response.data

    with app.app_context():
        req = db.session.get(BorrowingRequest, borrowing_request.id)
        assert req.status == 'accepted'
        assert req.reviewed_by == admin_user.id
        assert req.reviewed_at is not None


def test_permintaan_terima_with_note(
    app, logged_in_client, borrowing_request
):
    response = logged_in_client.post(
        '/admin/permintaan/terima/{}'.format(borrowing_request.id),
        data={'teacher_note': 'catatan guru'},
    )
    assert response.status_code == 200
    assert b'berhasil diterima' in response.data

    with app.app_context():
        req = db.session.get(BorrowingRequest, borrowing_request.id)
        assert req.teacher_note == 'catatan guru'


def test_permintaan_terima_not_authorized(
    regular_admin_client, borrowing_request
):
    response = regular_admin_client.post(
        '/admin/permintaan/terima/{}'.format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b'tidak berwenang' in response.data


def test_permintaan_terima_already_reviewed(
    app, logged_in_client, siswa_user, kategori_with_teacher
):
    with app.app_context():
        req = _make_request(
            siswa_user.id, kategori_with_teacher.id, status='accepted'
        )
        db.session.commit()
        req_id = req.id

    response = logged_in_client.post('/admin/permintaan/terima/{}'.format(req_id))
    assert response.status_code == 200
    assert b'sudah ditinjau' in response.data


def test_permintaan_terima_404(logged_in_client):
    response = logged_in_client.post('/admin/permintaan/terima/9999')
    assert response.status_code == 404


def test_permintaan_terima_anonymous_redirect(client):
    response = client.post('/admin/permintaan/terima/1')
    assert response.status_code == 302
    assert 'login' in response.location


def test_permintaan_terima_unlinked_superadmin_blocked(
    app, logged_in_client, siswa_user
):
    with app.app_context():
        cat = Category(name='Tanpa Pengawas')
        db.session.add(cat)
        db.session.flush()
        req = _make_request(siswa_user.id, cat.id)
        db.session.commit()
        req_id = req.id

    response = logged_in_client.post('/admin/permintaan/terima/{}'.format(req_id))
    assert response.status_code == 200
    assert b'tidak berwenang' in response.data


# ---- Tolak ----


def test_permintaan_tolak_success(
    app, logged_in_client, admin_user, borrowing_request
):
    response = logged_in_client.post(
        '/admin/permintaan/tolak/{}'.format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b'berhasil ditolak' in response.data

    with app.app_context():
        req = db.session.get(BorrowingRequest, borrowing_request.id)
        assert req.status == 'rejected'
        assert req.reviewed_by == admin_user.id


def test_permintaan_tolak_with_note(app, logged_in_client, borrowing_request):
    response = logged_in_client.post(
        '/admin/permintaan/tolak/{}'.format(borrowing_request.id),
        data={'teacher_note': 'alasan'},
    )
    assert response.status_code == 200
    assert b'berhasil ditolak' in response.data

    with app.app_context():
        req = db.session.get(BorrowingRequest, borrowing_request.id)
        assert req.teacher_note == 'alasan'


def test_permintaan_tolak_not_authorized(
    regular_admin_client, borrowing_request
):
    response = regular_admin_client.post(
        '/admin/permintaan/tolak/{}'.format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b'tidak berwenang' in response.data


def test_permintaan_tolak_already_reviewed(
    app, logged_in_client, siswa_user, kategori_with_teacher
):
    with app.app_context():
        req = _make_request(
            siswa_user.id, kategori_with_teacher.id, status='rejected'
        )
        db.session.commit()
        req_id = req.id

    response = logged_in_client.post('/admin/permintaan/tolak/{}'.format(req_id))
    assert response.status_code == 200
    assert b'sudah ditinjau' in response.data


def test_permintaan_tolak_404(logged_in_client):
    response = logged_in_client.post('/admin/permintaan/tolak/9999')
    assert response.status_code == 404


# ---- Batalkan keputusan ----


def test_permintaan_batalkan_success(
    app, logged_in_client, admin_user, siswa_user, kategori_with_teacher
):
    with app.app_context():
        req = _make_request(
            siswa_user.id, kategori_with_teacher.id,
            status='accepted', reviewed_by=admin_user.id,
        )
        db.session.commit()
        req_id = req.id

    response = logged_in_client.post(
        '/admin/permintaan/batalkan/{}'.format(req_id)
    )
    assert response.status_code == 200
    assert b'berhasil dibatalkan' in response.data

    with app.app_context():
        req = db.session.get(BorrowingRequest, req_id)
        assert req.status == 'pending'
        assert req.reviewed_by is None
        assert req.teacher_note is None


def test_permintaan_batalkan_not_authorized(
    app, regular_admin_client, admin_user, siswa_user, kategori_with_teacher
):
    with app.app_context():
        req = _make_request(
            siswa_user.id, kategori_with_teacher.id,
            status='accepted', reviewed_by=admin_user.id,
        )
        db.session.commit()
        req_id = req.id

    response = regular_admin_client.post(
        '/admin/permintaan/batalkan/{}'.format(req_id)
    )
    assert response.status_code == 200
    assert b'tidak berwenang' in response.data


def test_permintaan_batalkan_not_yet_reviewed(
    app, logged_in_client, borrowing_request
):
    response = logged_in_client.post(
        '/admin/permintaan/batalkan/{}'.format(borrowing_request.id)
    )
    assert response.status_code == 200
    assert b'belum ditinjau' in response.data


def test_permintaan_batalkan_after_cutoff(
    app, logged_in_client, admin_user, siswa_user, kategori_with_teacher
):
    with app.app_context():
        req = BorrowingRequest(
            student_id=siswa_user.id,
            category_id=kategori_with_teacher.id,
            date=date.today() - timedelta(days=1),
            status='accepted',
            reviewed_by=admin_user.id,
        )
        db.session.add(req)
        db.session.commit()
        req_id = req.id

    response = logged_in_client.post(
        '/admin/permintaan/batalkan/{}'.format(req_id)
    )
    assert response.status_code == 200
    assert b'tidak dapat dilakukan' in response.data


def test_permintaan_batalkan_reversible(
    app, logged_in_client, siswa_user, kategori_with_teacher
):
    with app.app_context():
        req = _make_request(siswa_user.id, kategori_with_teacher.id)
        db.session.commit()
        req_id = req.id

    logged_in_client.post('/admin/permintaan/terima/{}'.format(req_id))
    with app.app_context():
        assert db.session.get(BorrowingRequest, req_id).status == 'accepted'

    logged_in_client.post('/admin/permintaan/batalkan/{}'.format(req_id))
    with app.app_context():
        assert db.session.get(BorrowingRequest, req_id).status == 'pending'

    logged_in_client.post('/admin/permintaan/terima/{}'.format(req_id))
    with app.app_context():
        assert db.session.get(BorrowingRequest, req_id).status == 'accepted'


def test_permintaan_batalkan_404(logged_in_client):
    response = logged_in_client.post('/admin/permintaan/batalkan/9999')
    assert response.status_code == 404
