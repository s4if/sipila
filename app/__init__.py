import os
import time

# Pin proses ke WIB sebelum modul lain dipakai, agar date.today() /
# datetime.now() selalu mengembalikan waktu WIB (lihat helper.get_today()/get_now()).
os.environ.setdefault("TZ", "Asia/Jakarta")
if hasattr(time, "tzset"):
    time.tzset()

import click
from flask import Flask, redirect, url_for
from flask.cli import with_appcontext
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash

from .config import APP_CONFIG, Config
from .db import db, init_app
from .helper import htmx
from .models import Teacher

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.jinja_env.autoescape = True
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    init_app(app)
    csrf.init_app(app)
    htmx.init_app(app)

    @app.context_processor
    def inject_config():
        return dict(
            app_name=APP_CONFIG["app_name"],
        )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/")
    def root_dir():
        return redirect(url_for("auth.login_admin"))

    @click.command()
    @click.option(
        "--username", prompt="Username", help="The username to login with."
    )
    @click.option(
        "--password",
        prompt="Password",
        help="The password to login with.",
        hide_input=True,
    )
    @click.option(
        "--role",
        prompt="Role (admin/superadmin)",
        help="The role of the admin user.",
    )
    @with_appcontext
    def add_admin_user(username, password, role):
        hashed_password = generate_password_hash(
            password, method="pbkdf2:sha256", salt_length=16
        )
        admin_user = Teacher(username=username, password=hashed_password)
        admin_user.is_superadmin = role == "superadmin"
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user '{username}' added successfully!")

    @click.command()
    @click.option(
        "--username", prompt="Username", help="The username to login with."
    )
    @click.option(
        "--password",
        prompt="Password",
        help="The password to login with.",
        hide_input=True,
    )
    @click.option(
        "--role",
        prompt="Role (admin/superadmin)",
        help="The role of the admin user.",
    )
    @with_appcontext
    def change_admin_user(username, password, role):
        hashed_password = generate_password_hash(
            password, method="pbkdf2:sha256", salt_length=16
        )
        admin_user = Teacher.query.filter_by(username=username).first()
        if admin_user is None:
            print(f"Admin user '{username}' not found!")
        else:
            admin_user.password = hashed_password
            admin_user.is_superadmin = role == "superadmin"
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user '{username}' updated!")

    @click.command()
    @click.option(
        "--username", prompt="Username", help="The username to delete."
    )
    @with_appcontext
    def delete_admin_user(username):
        admin_user = Teacher.query.filter_by(username=username).first()
        if admin_user is None:
            print(f"Admin user '{username}' not found!")
        else:
            # Soft delete agar riwayat yang merujuk guru ini tetap utuh;
            # username ditandai supaya bisa dipakai ulang.
            admin_user.is_deleted = True
            admin_user.username = (
                f"{admin_user.username}#deleted#{admin_user.id}"
            )
            db.session.commit()
            print(f"Admin user '{username}' deleted!")

    @click.command("materialize-periods")
    @click.option(
        "--date",
        "target_date",
        default=None,
        help="Target date in YYYY-MM-DD format (default: today).",
    )
    @with_appcontext
    def materialize_periods(target_date):
        """Create daily borrowing requests from active loan periods."""
        from datetime import datetime

        from .periods import materialize_periods as run

        parsed = None
        if target_date:
            try:
                parsed = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise click.BadParameter(
                    "Date must be in YYYY-MM-DD format"
                )

        created = run(parsed)
        print(f"{created} borrowing request(s) created.")

    from . import admin, auth, siswa, supervisor

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(siswa.bp)
    app.register_blueprint(supervisor.bp)
    app.cli.add_command(add_admin_user)
    app.cli.add_command(delete_admin_user)
    app.cli.add_command(change_admin_user)
    app.cli.add_command(materialize_periods)

    return app


from .models import *  # noqa: E402, F403
