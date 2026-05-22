def test_admin_dashboard_redirects_anonymous(client):
    response = client.get('/admin/')
    assert response.status_code == 302
    assert 'login' in response.location


def test_admin_dashboard_returns_200_when_logged_in(logged_in_client):
    response = logged_in_client.get('/admin/')
    assert response.status_code == 200


def test_admin_password_page_redirects_anonymous(client):
    response = client.get('/admin/ganti_password')
    assert response.status_code == 302
    assert 'login' in response.location


def test_admin_password_page_get(logged_in_client):
    response = logged_in_client.get('/admin/ganti_password')
    assert response.status_code == 200
    assert b'password' in response.data.lower() or b'ganti' in response.data


def test_change_password_success(logged_in_client):
    response = logged_in_client.post('/admin/ganti_password', data={
        'current_password': 'secret',
        'new_password': 'newsecret123',
        'confirm_password': 'newsecret123',
    })
    assert response.status_code == 200
    assert b'berhasil' in response.data.lower()


def test_change_password_mismatch(logged_in_client):
    response = logged_in_client.post('/admin/ganti_password', data={
        'current_password': 'secret',
        'new_password': 'newpass1',
        'confirm_password': 'newpass2',
    })
    assert response.status_code == 200
    assert b'tidak sesuai' in response.data


def test_change_password_wrong_current(logged_in_client):
    response = logged_in_client.post('/admin/ganti_password', data={
        'current_password': 'wrongpassword',
        'new_password': 'newsecret123',
        'confirm_password': 'newsecret123',
    })
    assert response.status_code == 200
    assert b'tidak sesuai' in response.data or b'salah' in response.data


# ---- Guru CRUD tests ----


def test_guru_list_redirects_anonymous(client):
    response = client.get('/admin/guru')
    assert response.status_code == 302
    assert 'login' in response.location


def test_guru_list_returns_200(logged_in_client):
    response = logged_in_client.get('/admin/guru')
    assert response.status_code == 200
    assert b'Data Guru' in response.data


def test_guru_data_returns_json(logged_in_client, admin_user):
    response = logged_in_client.get('/admin/guru/data')
    assert response.status_code == 200
    data = response.get_json()
    assert 'data' in data
    assert len(data['data']) >= 1
    assert data['data'][0]['username'] == 'admin'


def test_guru_tambah_page_get(logged_in_client):
    response = logged_in_client.get('/admin/guru/tambah')
    assert response.status_code == 200
    assert b'Tambah Guru' in response.data


def test_guru_tambah_success(logged_in_client, app):
    response = logged_in_client.post('/admin/guru/tambah', data={
        'username': 'guru1',
        'name': 'Guru Satu',
        'contact_person': '081234567890',
        'password': 'password123',
    })
    assert response.status_code == 200
    assert b'berhasil ditambahkan' in response.data

    with app.app_context():
        from app.models import Admin
        guru = Admin.query.filter_by(username='guru1').first()
        assert guru is not None
        assert guru.name == 'Guru Satu'
        assert guru.is_superadmin is False


def test_guru_tambah_duplicate_username(logged_in_client):
    response = logged_in_client.post('/admin/guru/tambah', data={
        'username': 'admin',
        'name': 'Duplikat',
        'password': 'password123',
    })
    assert response.status_code == 200
    assert b'sudah digunakan' in response.data


def test_guru_tambah_without_password(logged_in_client):
    response = logged_in_client.post('/admin/guru/tambah', data={
        'username': 'guru2',
        'name': 'Guru Dua',
        'password': '',
    })
    assert response.status_code == 200
    assert b'wajib diisi' in response.data


def test_guru_edit_page_get(logged_in_client, admin_user):
    response = logged_in_client.get(f'/admin/guru/edit/{admin_user.id}')
    assert response.status_code == 200
    assert b'Edit Guru' in response.data


def test_guru_edit_success(logged_in_client, app, admin_user):
    response = logged_in_client.post(f'/admin/guru/edit/{admin_user.id}', data={
        'username': 'admin',
        'name': 'Admin Baru',
        'contact_person': '089999',
        'password': '',
    })
    assert response.status_code == 200
    assert b'berhasil diperbarui' in response.data

    with app.app_context():
        from app.models import Admin
        guru = Admin.query.get(admin_user.id)
        assert guru.name == 'Admin Baru'


def test_guru_edit_duplicate_username(logged_in_client, app):
    from werkzeug.security import generate_password_hash
    from app import db
    from app.models import Admin
    with app.app_context():
        guru2 = Admin(
            username='guru2',
            password=generate_password_hash('pass'),
        )
        db.session.add(guru2)
        db.session.commit()
        guru2_id = guru2.id

    response = logged_in_client.post(f'/admin/guru/edit/{guru2_id}', data={
        'username': 'admin',
        'name': 'Guru Dua',
        'password': '',
    })
    assert response.status_code == 200
    assert b'sudah digunakan' in response.data


def test_guru_edit_with_new_password(logged_in_client, app, admin_user):
    response = logged_in_client.post(f'/admin/guru/edit/{admin_user.id}', data={
        'username': 'admin',
        'name': 'Admin',
        'password': 'newpassword456',
    })
    assert response.status_code == 200
    assert b'berhasil diperbarui' in response.data

    with app.app_context():
        from werkzeug.security import check_password_hash
        from app.models import Admin
        guru = Admin.query.get(admin_user.id)
        assert check_password_hash(guru.password, 'newpassword456')


def test_guru_hapus_success(logged_in_client, app):
    from werkzeug.security import generate_password_hash
    from app.models import Admin
    from app import db
    with app.app_context():
        guru = Admin(
            username='hapus_guru',
            password=generate_password_hash('pass'),
        )
        db.session.add(guru)
        db.session.commit()
        guru_id = guru.id

    response = logged_in_client.post('/admin/guru/hapus', data={'id': guru_id})
    assert response.status_code == 200
    assert b'berhasil dihapus' in response.data


def test_guru_hapus_self_blocked(logged_in_client, admin_user):
    response = logged_in_client.post('/admin/guru/hapus', data={
        'id': admin_user.id,
    })
    assert response.status_code == 200
    assert b'tidak dapat menghapus' in response.data.lower()


def test_guru_hapus_404(logged_in_client):
    response = logged_in_client.post('/admin/guru/hapus', data={'id': 9999})
    assert response.status_code == 404
