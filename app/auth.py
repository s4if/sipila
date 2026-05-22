from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__)


@bp.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    from .forms import LoginForm

    form = LoginForm(request.form)
    if request.method == "GET":
        return render_template("login/index.jinja", form=form)
    else:
        from .models import Admin

        a = Admin.query.filter_by(username=request.form["username"]).first()
        if a and check_password_hash(a.password, request.form["password"]):
            session["logged_in"] = True
            session["is_admin"] = True
            session["is_superadmin"] = a.is_superadmin
            session["admin_name"] = a.username
            return redirect(url_for("admin.beranda"))
        else:
            error = "Invalid admin username or password"
            return render_template("login/index.jinja", form=form, error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_admin"))
