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


@pytest.fixture
def regular_admin(app):
    from werkzeug.security import generate_password_hash
    from app.models import Teacher
    user = Teacher(
        username='guru',
        name='Guru Biasa',
        password=generate_password_hash('secret'),
        is_superadmin=False,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def regular_admin_client(client, regular_admin):
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['is_admin'] = True
        sess['is_superadmin'] = False
        sess['admin_name'] = regular_admin.username
    return client


@pytest.fixture
def siswa_user(app):
    from werkzeug.security import generate_password_hash
    from app.models import ClassGroup, Student
    cg = ClassGroup(name='1', grade_level='X', major='TJKT')
    db.session.add(cg)
    db.session.flush()
    user = Student(
        student_id='S001',
        name='Siswa Test',
        password=generate_password_hash('rahasia'),
        class_group_id=cg.id,
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def logged_in_siswa_client(client, siswa_user):
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['is_admin'] = False
        sess['student_id'] = siswa_user.student_id
        sess['student_name'] = siswa_user.name
        sess['student_db_id'] = siswa_user.id
    return client


@pytest.fixture
def kategori_with_teacher(app, admin_user):
    from app.models import Category, CategoryTeacher
    cat = Category(name='Kategori Test')
    db.session.add(cat)
    db.session.flush()
    db.session.add(CategoryTeacher(category_id=cat.id, teacher_id=admin_user.id))
    db.session.commit()
    return cat


@pytest.fixture
def borrowing_request(app, siswa_user, kategori_with_teacher):
    from datetime import date
    from app.models import BorrowingRequest
    req = BorrowingRequest(
        student_id=siswa_user.id,
        category_id=kategori_with_teacher.id,
        date=date.today(),
        status='pending',
    )
    db.session.add(req)
    db.session.commit()
    return req
