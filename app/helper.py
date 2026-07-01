# isinya decorator untuk fungsi2 tertentu

import functools
import re
from datetime import timedelta, timezone

from flask import make_response, redirect, render_template, session, url_for
from flask_htmx import HTMX

htmx = HTMX()

WIB = timezone(timedelta(hours=7))


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
