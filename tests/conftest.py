import pytest
from app import create_app, db


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test',
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    from werkzeug.security import generate_password_hash
    from app.models import Teacher
    user = Teacher(
        username='admin',
        password=generate_password_hash('secret'),
        is_superadmin=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def logged_in_client(client, admin_user):
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['is_admin'] = True
        sess['is_superadmin'] = True
        sess['admin_name'] = admin_user.username
    return client
