from app.models import Teacher


def test_create_admin(app):
    with app.app_context():
        admin = Teacher(username='testuser', password='hashedpwd', is_superadmin=False)
        assert admin.username == 'testuser'
        assert admin.password == 'hashedpwd'
        assert admin.is_superadmin is False


def test_create_superadmin(app):
    with app.app_context():
        admin = Teacher(username='super', password='hashedpwd', is_superadmin=True)
        assert admin.is_superadmin is True


def test_admin_repr(app):
    with app.app_context():
        admin = Teacher(username='repruser', password='pwd')
        assert repr(admin) == '<Teacher repruser>'
