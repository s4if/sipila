# isinya decorator untuk fungsi2 tertentu

import base64
import functools
import hashlib
import re
import secrets
from datetime import date, datetime

from flask import (
    current_app,
    make_response,
    redirect,
    render_template,
    session,
    url_for,
)
from flask_htmx import HTMX

htmx = HTMX()


def get_today():
    # Satu-satunya sumber "hari ini" di aplikasi. Naive WIB karena proses
    # sudah di-pin ke Asia/Jakarta (lihat app/__init__.py).
    return date.today()


def get_now():
    # Satu-satunya sumber "sekarang" di aplikasi. Naive WIB.
    return datetime.now()


# --- Captcha login ---
# Karakter tanpa yang mirip (0/O, 1/I/L) supaya mudah dibaca pengguna.
_CAPTCHA_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_CAPTCHA_LENGTH = 5


def captcha_enabled():
    # Bisa dimatikan lewat config, mis. saat testing (lihat Config).
    return current_app.config.get("LOGIN_CAPTCHA_ENABLED", True)


def generate_captcha_text():
    return "".join(
        secrets.choice(_CAPTCHA_ALPHABET) for _ in range(_CAPTCHA_LENGTH)
    )


def captcha_hash(text):
    # Disimpan sebagai hash di session agar jawaban tidak terbaca dari cookie
    # (session Flask = cookie yang ditandatangani, bukan dienkripsi).
    # Normalisasi ke uppercase sehingga pencocokan case-insensitive.
    return hashlib.sha256(text.strip().upper().encode("utf-8")).hexdigest()


def captcha_image_base64(text):
    # Hasilkan gambar captcha sebagai string base64 (untuk <img src="...">).
    from captcha.image import ImageCaptcha

    image = ImageCaptcha()
    data = image.generate(text)
    return base64.b64encode(data.read()).decode("ascii")


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "logged_in" not in session or "is_admin" not in session:
            return redirect(url_for("auth.login_siswa"))
        elif not session["logged_in"]:
            session.clear()
            return redirect(url_for("auth.login_siswa"))
        elif session.get("is_admin"):
            return redirect(url_for("admin.beranda"))
        elif "student_id" not in session or "student_db_id" not in session:
            return redirect(url_for("auth.login_siswa"))
        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if (
            "is_admin" not in session
            or "logged_in" not in session
            or "admin_name" not in session
        ):
            return redirect(url_for("auth.login_admin"))
        elif not session["is_admin"]:
            session.clear()
            return redirect(url_for("auth.login_admin"))
        return view(**kwargs)

    return wrapped_view


def superadmin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if (
            "is_admin" not in session
            or "logged_in" not in session
            or "admin_name" not in session
        ):
            return redirect(url_for("auth.login_admin"))
        elif not session["is_admin"]:
            session.clear()
            return redirect(url_for("auth.login_admin"))
        elif "is_superadmin" not in session or not session["is_superadmin"]:
            return redirect(url_for("admin.beranda"))
        return view(**kwargs)

    return wrapped_view


def hx_render(template, push_url=None, **kwargs):
    kwargs.setdefault(
        "username", session.get("username") or session.get("admin_name")
    )
    kwargs.setdefault("is_superadmin", session.get("is_superadmin"))
    kwargs.setdefault("student_name", session.get("student_name"))
    kwargs.setdefault("is_htmx", htmx)
    if push_url:
        resp = make_response(render_template(template, **kwargs))
        if push_url.startswith("/") or push_url.startswith("http"):
            resp.headers["HX-Push-Url"] = push_url
        else:
            resp.headers["HX-Push-Url"] = url_for(push_url)
        return resp
    return render_template(template, **kwargs)


def get_active_ban(student_id):
    from app.models import StudentBan

    today = get_today()
    return StudentBan.query.filter(
        StudentBan.student_id == student_id,
        StudentBan.start_date <= today,
        StudentBan.end_date >= today,
    ).first()


def js_escape(input_str):
    # Escape string untuk konteks atribut JS string literal (single-quoted)
    # sanitize() tidak membuang kutip/backslash, jadi nilai yang disisipkan
    # ke onclick="fn('...')" harus di-escape agar tidak memutus string atau
    # memicu stored-XSS (mis. nama "O'Brien" atau "');alert(1)//").
    if input_str is None:
        return ""
    if not isinstance(input_str, str):
        input_str = str(input_str)
    input_str = input_str.replace("\\", "\\\\")
    input_str = input_str.replace("'", "\\'")
    input_str = input_str.replace("\n", "\\n")
    input_str = input_str.replace("\r", "\\r")
    input_str = input_str.replace("</", "<\\/")
    return input_str


def sanitize(input_str):
    # check if it is None then return None
    if input_str is None:
        return None

    # check if it is a string then return
    if not isinstance(input_str, str):
        return input_str

    # Remove <script> tags and JavaScript event handlers
    input_str = re.sub(
        r"<script\b[^>]*>(.*?)</script>", "", input_str, flags=re.IGNORECASE
    )

    # Remove tags that commonly lead to XSS if not needed (like iframe, object, embed, etc.)
    input_str = re.sub(
        r"</?(iframe|embed|object|form|input|button|style|link|meta)\b[^>]*>",
        "",
        input_str,
        flags=re.IGNORECASE,
    )

    # Remove event handler attributes (e.g., onclick, onerror)
    input_str = re.sub(
        r'\s(on\w+)\s*=\s*(".*?"|\'.*?\'|[^\s>]+)',
        "",
        input_str,
        flags=re.IGNORECASE,
    )

    # Remove JavaScript URLs in href or src attributes
    input_str = re.sub(
        r'\s(href|src)\s*=\s*("|\')?javascript:[^"\']*("|\')?',
        "",
        input_str,
        flags=re.IGNORECASE,
    )

    return input_str
