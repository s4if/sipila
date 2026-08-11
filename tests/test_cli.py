from werkzeug.security import check_password_hash

from app import db
from app.models import Teacher


# ---- add-admin-user ----


def test_add_admin_user_creates_superadmin(runner, app):
    result = runner.invoke(
        args=[
            "add-admin-user",
            "--username",
            "baru",
            "--password",
            "rahasia",
            "--role",
            "superadmin",
        ]
    )
    assert result.exit_code == 0
    assert "added successfully" in result.output

    with app.app_context():
        user = Teacher.query.filter_by(username="baru").one()
        assert user.is_superadmin is True


def test_add_admin_user_creates_regular_admin(runner, app):
    result = runner.invoke(
        args=[
            "add-admin-user",
            "--username",
            "guru1",
            "--password",
            "rahasia",
            "--role",
            "admin",
        ]
    )
    assert result.exit_code == 0

    with app.app_context():
        user = Teacher.query.filter_by(username="guru1").one()
        assert user.is_superadmin is False


def test_add_admin_user_password_is_hashed(runner, app):
    runner.invoke(
        args=[
            "add-admin-user",
            "--username",
            "aman",
            "--password",
            "rahasia",
            "--role",
            "admin",
        ]
    )

    with app.app_context():
        user = Teacher.query.filter_by(username="aman").one()
        # Password tidak disimpan apa adanya
        assert user.password != "rahasia"
        # Hash tetap bisa diverifikasi terhadap plaintext
        assert check_password_hash(user.password, "rahasia")


# ---- change-admin-user ----


def test_change_admin_user_updates_password_and_role(runner, app, admin_user):
    result = runner.invoke(
        args=[
            "change-admin-user",
            "--username",
            "admin",
            "--password",
            "passwordbaru",
            "--role",
            "admin",
        ]
    )
    assert result.exit_code == 0
    assert "updated" in result.output

    with app.app_context():
        user = Teacher.query.filter_by(username="admin").one()
        assert user.is_superadmin is False
        assert check_password_hash(user.password, "passwordbaru")
        # Password lama tidak lagi valid
        assert not check_password_hash(user.password, "secret")


def test_change_admin_user_promotes_to_superadmin(
    runner, app, regular_admin
):
    result = runner.invoke(
        args=[
            "change-admin-user",
            "--username",
            "guru",
            "--password",
            "rahasia",
            "--role",
            "superadmin",
        ]
    )
    assert result.exit_code == 0

    with app.app_context():
        user = Teacher.query.filter_by(username="guru").one()
        assert user.is_superadmin is True


def test_change_admin_user_nonexistent(runner, app):
    result = runner.invoke(
        args=[
            "change-admin-user",
            "--username",
            "tidakada",
            "--password",
            "rahasia",
            "--role",
            "admin",
        ]
    )
    assert result.exit_code == 0
    assert "not found" in result.output

    with app.app_context():
        assert Teacher.query.filter_by(username="tidakada").first() is None


# ---- delete-admin-user ----


def test_delete_admin_user_removes_user(runner, app, admin_user):
    result = runner.invoke(args=["delete-admin-user", "--username", "admin"])
    assert result.exit_code == 0
    assert "deleted" in result.output

    with app.app_context():
        assert Teacher.query.filter_by(username="admin").first() is None


def test_delete_admin_user_nonexistent(runner, app):
    result = runner.invoke(args=["delete-admin-user", "--username", "hantu"])
    assert result.exit_code == 0
    assert "not found" in result.output


def test_delete_admin_user_only_removes_target(runner, app):
    with app.app_context():
        db.session.add(Teacher(username="target", password="x"))
        db.session.add(Teacher(username="lain", password="y"))
        db.session.commit()

    runner.invoke(args=["delete-admin-user", "--username", "target"])

    with app.app_context():
        assert Teacher.query.filter_by(username="target").first() is None
        assert Teacher.query.filter_by(username="lain").one()
