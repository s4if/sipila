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
