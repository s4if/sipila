from flask import (
    Blueprint,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__)


def _new_captcha():
    # Buat captcha baru, simpan hash jawabannya di session, kembalikan gambar
    # base64 (atau None bila captcha dimatikan lewat config).
    from .helper import (
        captcha_enabled,
        captcha_hash,
        captcha_image_base64,
        generate_captcha_text,
    )

    if not captcha_enabled():
        return None
    text = generate_captcha_text()
    session["captcha_answer"] = captcha_hash(text)
    return captcha_image_base64(text)


def verify_captcha():
    # Cocokkan captcha yang dikirim dengan hash di session. Sekali pakai:
    # jawaban di-pop supaya tidak bisa di-replay.
    from .helper import captcha_enabled, captcha_hash

    if not captcha_enabled():
        return True
    submitted = (request.form.get("captcha") or "").strip().upper()
    expected = session.pop("captcha_answer", None)
    if not submitted or not expected:
        return False
    return captcha_hash(submitted) == expected


@bp.route("/login/captcha")
def captcha():
    # Endpoint htmx: kembalikan <img> captcha baru (base64) untuk di-swap ke
    # dalam #captcha-image tanpa reload halaman.
    img = _new_captcha()
    if img is None:
        return make_response("")
    html = (
        '<img class="captcha-img" alt="Kode keamanan" '
        'src="data:image/png;base64,{0}">'.format(img)
    )
    return make_response(html)


@bp.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    from .forms import LoginForm

    form = LoginForm(request.form)
    if request.method == "GET":
        return render_template(
            "login/index.jinja", form=form, captcha_img=_new_captcha()
        )
    else:
        if not verify_captcha():
            error = "Kode keamanan salah"
            return render_template(
                "login/index.jinja",
                form=form,
                captcha_img=_new_captcha(),
                error=error,
            )

        from .models import Teacher

        a = Teacher.query.filter_by(
            username=request.form["username"], is_deleted=False
        ).first()
        if a and check_password_hash(a.password, request.form["password"]):
            session.pop("captcha_answer", None)
            session["logged_in"] = True
            session["is_admin"] = True
            session["is_superadmin"] = a.is_superadmin
            session["admin_name"] = a.username
            return redirect(url_for("admin.beranda"))
        else:
            error = "Invalid admin username or password"
            return render_template(
                "login/index.jinja",
                form=form,
                captcha_img=_new_captcha(),
                error=error,
            )


@bp.route("/login/siswa", methods=["GET", "POST"])
def login_siswa():
    from .forms import SiswaLoginForm

    form = SiswaLoginForm(request.form)
    if request.method == "GET":
        return render_template(
            "login/siswa.jinja", form=form, captcha_img=_new_captcha()
        )
    else:
        if not verify_captcha():
            error = "Kode keamanan salah"
            return render_template(
                "login/siswa.jinja",
                form=form,
                captcha_img=_new_captcha(),
                error=error,
            )

        from .models import Student

        siswa = Student.query.filter_by(
            student_id=request.form["student_id"], is_deleted=False
        ).first()
        if siswa and check_password_hash(
            siswa.password, request.form["password"]
        ):
            session.pop("captcha_answer", None)
            session["logged_in"] = True
            session["is_admin"] = False
            session["student_id"] = siswa.student_id
            session["student_name"] = siswa.name
            session["student_db_id"] = siswa.id
            return redirect(url_for("siswa.beranda"))
        else:
            error = "NIS atau password salah"
            return render_template(
                "login/siswa.jinja",
                form=form,
                captcha_img=_new_captcha(),
                error=error,
            )


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_admin"))
