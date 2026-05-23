def test_kategori_list_redirects_anonymous(client):
    response = client.get('/admin/kategori')
    assert response.status_code == 302
    assert 'login' in response.location


def test_kategori_list_returns_200(logged_in_client):
    response = logged_in_client.get('/admin/kategori')
    assert response.status_code == 200
    assert b'Data Kategori' in response.data


def test_kategori_data_returns_json(logged_in_client):
    response = logged_in_client.get('/admin/kategori/data')
    assert response.status_code == 200
    data = response.get_json()
    assert 'data' in data


def test_kategori_tambah_page_get(logged_in_client):
    response = logged_in_client.get('/admin/kategori/tambah')
    assert response.status_code == 200
    assert b'Tambah Kategori' in response.data


def test_kategori_tambah_success(logged_in_client, app):
    response = logged_in_client.post('/admin/kategori/tambah', data={
        'name': 'Persiapan Lomba',
        'teachers': [],
    })
    assert response.status_code == 200
    assert b'berhasil ditambahkan' in response.data

    with app.app_context():
        from app.models import Category
        cat = Category.query.filter_by(name='Persiapan Lomba').first()
        assert cat is not None


def test_kategori_tambah_with_teachers(logged_in_client, app, admin_user):
    response = logged_in_client.post('/admin/kategori/tambah', data={
        'name': 'Tugas Pelajaran',
        'teachers': [admin_user.id],
    })
    assert response.status_code == 200
    assert b'berhasil ditambahkan' in response.data

    with app.app_context():
        from app.models import Category, CategoryTeacher
        cat = Category.query.filter_by(name='Tugas Pelajaran').first()
        assert cat is not None
        links = CategoryTeacher.query.filter_by(category_id=cat.id).all()
        assert len(links) == 1
        assert links[0].teacher_id == admin_user.id


def test_kategori_tambah_duplicate_name(logged_in_client, app):
    from app import db
    from app.models import Category
    with app.app_context():
        db.session.add(Category(name='Pembuatan Proposal'))
        db.session.commit()

    response = logged_in_client.post('/admin/kategori/tambah', data={
        'name': 'Pembuatan Proposal',
        'teachers': [],
    })
    assert response.status_code == 200
    assert b'sudah digunakan' in response.data


def test_kategori_edit_page_get(logged_in_client, app):
    from app import db
    from app.models import Category
    with app.app_context():
        cat = Category(name='Edit Test')
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    response = logged_in_client.get(f'/admin/kategori/edit/{cat_id}')
    assert response.status_code == 200
    assert b'Edit Kategori' in response.data


def test_kategori_edit_success(logged_in_client, app):
    from app import db
    from app.models import Category
    with app.app_context():
        cat = Category(name='Old Name')
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    response = logged_in_client.post(f'/admin/kategori/edit/{cat_id}', data={
        'name': 'New Name',
        'teachers': [],
    })
    assert response.status_code == 200
    assert b'berhasil diperbarui' in response.data

    with app.app_context():
        cat = Category.query.get(cat_id)
        assert cat.name == 'New Name'


def test_kategori_edit_duplicate_name(logged_in_client, app):
    from app import db
    from app.models import Category
    with app.app_context():
        db.session.add(Category(name='Existing'))
        cat2 = Category(name='To Edit')
        db.session.add(cat2)
        db.session.commit()
        cat2_id = cat2.id

    response = logged_in_client.post(f'/admin/kategori/edit/{cat2_id}', data={
        'name': 'Existing',
        'teachers': [],
    })
    assert response.status_code == 200
    assert b'sudah digunakan' in response.data


def test_kategori_edit_updates_teachers(logged_in_client, app, admin_user):
    from app import db
    from app.models import Category, CategoryTeacher
    with app.app_context():
        cat = Category(name='With Teachers')
        db.session.add(cat)
        db.session.commit()
        db.session.add(CategoryTeacher(category_id=cat.id, teacher_id=admin_user.id))
        db.session.commit()
        cat_id = cat.id

    response = logged_in_client.post(f'/admin/kategori/edit/{cat_id}', data={
        'name': 'With Teachers',
        'teachers': [],
    })
    assert response.status_code == 200
    assert b'berhasil diperbarui' in response.data

    with app.app_context():
        links = CategoryTeacher.query.filter_by(category_id=cat_id).all()
        assert len(links) == 0


def test_kategori_hapus_success(logged_in_client, app):
    from app import db
    from app.models import Category
    with app.app_context():
        cat = Category(name='To Delete')
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    response = logged_in_client.post('/admin/kategori/hapus', data={'id': cat_id})
    assert response.status_code == 200
    assert b'berhasil dihapus' in response.data

    with app.app_context():
        assert Category.query.get(cat_id) is None


def test_kategori_hapus_cascades_links(logged_in_client, app, admin_user):
    from app import db
    from app.models import Category, CategoryTeacher
    with app.app_context():
        cat = Category(name='Cascade Delete')
        db.session.add(cat)
        db.session.commit()
        db.session.add(CategoryTeacher(category_id=cat.id, teacher_id=admin_user.id))
        db.session.commit()
        cat_id = cat.id

    response = logged_in_client.post('/admin/kategori/hapus', data={'id': cat_id})
    assert response.status_code == 200
    assert b'berhasil dihapus' in response.data

    with app.app_context():
        links = CategoryTeacher.query.filter_by(category_id=cat_id).all()
        assert len(links) == 0


def test_kategori_hapus_404(logged_in_client):
    response = logged_in_client.post('/admin/kategori/hapus', data={'id': 9999})
    assert response.status_code == 404
