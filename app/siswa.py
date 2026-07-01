from datetime import datetime, timedelta

from flask import Blueprint, jsonify, redirect, request, session, url_for

from .db import db
from .forms import PermintaanSiswaForm
from .helper import WIB, hx_render, login_required, sanitize
from .models import BorrowingRequest, Category

bp = Blueprint("siswa", __name__, url_prefix="/siswa")


def _date_range():
    min_date = datetime.now(WIB).date()
    max_date = min_date + timedelta(days=7)
    return min_date, max_date


@bp.route("/")
@login_required
def beranda():
    return hx_render("siswa/beranda.jinja")


@bp.route("/permintaan/data")
@login_required
def permintaan_data():
    from sqlalchemy.orm import joinedload

    student_db_id = session["student_db_id"]
    today = datetime.now(WIB).date()
    start_date = today - timedelta(days=7)
    requests = (
        BorrowingRequest.query.options(
            joinedload(BorrowingRequest.category),
        )
        .filter_by(student_id=student_db_id)
        .filter(BorrowingRequest.date >= start_date)
        .order_by(BorrowingRequest.date.desc())
        .all()
    )

    status_badges = {
        "pending": '<span class="badge bg-warning text-dark">Pending</span>',
        "accepted": '<span class="badge bg-success">Diterima</span>',
        "rejected": '<span class="badge bg-danger">Ditolak</span>',
    }

    data = []
    for i, req in enumerate(requests, 1):
        is_pending = req.status == "pending"
        detail_btn = (
            '<a class="btn btn-sm btn-info text-white" '
            f'onclick="detail_permintaan({req.id})">'
            '<i class="bi bi-eye"></i> Detail</a>'
        )
        edit_btn = (
            '<a class="btn btn-sm btn-warning ms-1" '
            f'onclick="edit_permintaan({req.id})">'
            '<i class="bi bi-pencil"></i> Edit</a>'
        )
        cancel_btn = (
            '<button type="button" class="btn btn-sm btn-danger ms-1" '
            f"onclick=\"batal_permintaan({req.id}, '{req.date.strftime('%d/%m/%Y')}')\">"
            '<i class="bi bi-x-circle"></i> Batal</button>'
        )
        actions = detail_btn
        if is_pending:
            actions += edit_btn + cancel_btn

        data.append(
            {
                "no": i,
                "date": req.date.strftime("%d/%m/%Y") if req.date else "-",
                "category": req.category.name if req.category else "-",
                "status": status_badges.get(req.status, req.status),
                "student_note": req.student_note or "-",
                "teacher_note": req.teacher_note or "-",
                "actions": actions,
            }
        )
    return jsonify(data=data)


@bp.route("/permintaan/tambah", methods=["GET", "POST"])
@login_required
def permintaan_tambah():
    min_date, max_date = _date_range()
    form = PermintaanSiswaForm()
    form.category_id.choices = [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]
    if request.method == "GET":
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form, req=None,
            min_date=min_date.isoformat(), max_date=max_date.isoformat(),
        )

    if not form.validate_on_submit():
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form, req=None,
            min_date=min_date.isoformat(), max_date=max_date.isoformat(),
        )

    notif = {}
    if form.date.data < min_date or form.date.data > max_date:
        notif["error"] = "Tanggal harus dalam rentang hari ini sampai 7 hari ke depan"
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form, req=None,
            min_date=min_date.isoformat(), max_date=max_date.isoformat(),
            **notif,
        )

    student_db_id = session["student_db_id"]
    existing = BorrowingRequest.query.filter_by(
        student_id=student_db_id, date=form.date.data
    ).first()
    if existing:
        notif["error"] = "Anda sudah mengajukan permintaan untuk tanggal tersebut"
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form, req=None,
            min_date=min_date.isoformat(), max_date=max_date.isoformat(),
            **notif,
        )

    req = BorrowingRequest(
        student_id=student_db_id,
        category_id=form.category_id.data,
        date=form.date.data,
        status="pending",
        student_note=sanitize(form.student_note.data) or None,
    )
    db.session.add(req)
    db.session.commit()
    notif["success"] = "Permintaan peminjaman berhasil dibuat"
    return hx_render("siswa/beranda.jinja", push_url="siswa.beranda", **notif)


@bp.route("/permintaan/edit/<int:id>", methods=["GET", "POST"])
@login_required
def permintaan_edit(id):
    min_date, max_date = _date_range()
    req = BorrowingRequest.query.get_or_404(id)
    if req.student_id != session["student_db_id"]:
        return redirect(url_for("siswa.beranda"))
    if req.status != "pending":
        return redirect(url_for("siswa.beranda"))

    form = PermintaanSiswaForm(obj=req)
    form.category_id.choices = [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]
    if request.method == "GET":
        form.date.data = req.date
        form.category_id.data = req.category_id
        form.student_note.data = req.student_note
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form, req=req,
            min_date=min_date.isoformat(), max_date=max_date.isoformat(),
        )

    if not form.validate_on_submit():
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form, req=req,
            min_date=min_date.isoformat(), max_date=max_date.isoformat(),
        )

    notif = {}
    if form.date.data < min_date or form.date.data > max_date:
        notif["error"] = "Tanggal harus dalam rentang hari ini sampai 7 hari ke depan"
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form, req=req,
            min_date=min_date.isoformat(), max_date=max_date.isoformat(),
            **notif,
        )

    student_db_id = session["student_db_id"]
    existing = BorrowingRequest.query.filter(
        BorrowingRequest.student_id == student_db_id,
        BorrowingRequest.date == form.date.data,
        BorrowingRequest.id != id,
    ).first()
    if existing:
        notif["error"] = "Anda sudah mengajukan permintaan untuk tanggal tersebut"
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form, req=req,
            min_date=min_date.isoformat(), max_date=max_date.isoformat(),
            **notif,
        )

    req.category_id = form.category_id.data
    req.date = form.date.data
    req.student_note = sanitize(form.student_note.data) or None
    db.session.commit()
    notif["success"] = "Permintaan berhasil diperbarui"
    return hx_render("siswa/beranda.jinja", push_url="siswa.beranda", **notif)


@bp.route("/permintaan/batal", methods=["POST"])
@login_required
def permintaan_batal():
    id = request.form.get("id", type=int)
    req = BorrowingRequest.query.get_or_404(id)
    notif = {}
    if req.student_id != session["student_db_id"]:
        notif["error"] = "Anda tidak berwenang membatalkan permintaan ini"
    elif req.status != "pending":
        notif["error"] = "Hanya permintaan berstatus pending yang dapat dibatalkan"
    else:
        db.session.delete(req)
        db.session.commit()
        notif["success"] = "Permintaan berhasil dibatalkan"
    return hx_render("siswa/beranda.jinja", push_url="siswa.beranda", **notif)


@bp.route("/permintaan/<int:id>")
@login_required
def permintaan_detail(id):
    from sqlalchemy.orm import joinedload

    req = BorrowingRequest.query.options(
        joinedload(BorrowingRequest.category),
        joinedload(BorrowingRequest.reviewer),
    ).get_or_404(id)

    if req.student_id != session["student_db_id"]:
        return redirect(url_for("siswa.beranda"))

    return hx_render("siswa/permintaan_detail.jinja", req=req)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_siswa"))
