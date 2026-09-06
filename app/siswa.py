from datetime import timedelta

from flask import Blueprint, jsonify, redirect, request, session, url_for

from .db import db
from .forms import PermintaanSiswaForm
from .helper import get_today, hx_render, login_required, sanitize
from .models import (
    AssignedReviewer,
    BorrowingRequest,
    Category,
    CategoryTeacher,
    StudentBan,
    Teacher,
)
from .periods import get_active_period_for

bp = Blueprint("siswa", __name__, url_prefix="/siswa")


def _date_range():
    min_date = get_today()
    max_date = min_date + timedelta(days=7)
    return min_date, max_date


def _category_choices():
    # Kategori opsional: pilihan pertama "Tanpa Kategori" (nilai kosong)
    return [("", "Tanpa Kategori")] + [
        (c.id, c.name)
        for c in Category.query.filter_by(is_deleted=False)
        .order_by(Category.name)
        .all()
    ]


def _reviewer_choices():
    # Siswa bebas memilih guru mana pun yang masih aktif
    return [
        (t.id, t.name or t.username)
        for t in Teacher.query.filter_by(is_deleted=False)
        .order_by(Teacher.name)
        .all()
    ]


def _category_default_reviewers(category_id):
    # Preselect bawaan: guru pengawas kategori (yang masih aktif)
    return [
        t.id
        for t in Teacher.query.join(
            CategoryTeacher, CategoryTeacher.teacher_id == Teacher.id
        )
        .filter(
            CategoryTeacher.category_id == category_id,
            Teacher.is_deleted.is_(False),
        )
        .all()
    ]


def _saved_reviewers(form, req):
    # Penunjukan tersimpan; guru yang sudah dihapus tidak ditawarkan lagi
    active_ids = {tid for tid, _ in form.reviewers.choices}
    return [
        ar.teacher_id
        for ar in req.assigned_reviewers
        if ar.teacher_id in active_ids
    ]


@bp.route("/")
@login_required
def beranda():
    student_db_id = session["student_db_id"]
    active_ban = StudentBan.query.filter(
        StudentBan.student_id == student_db_id,
        StudentBan.start_date <= get_today(),
        StudentBan.end_date >= get_today(),
    ).first()

    return hx_render(
        "siswa/beranda.jinja",
        has_active_ban=active_ban is not None,
        active_ban=active_ban,
    )


@bp.route("/permintaan/data")
@login_required
def permintaan_data():
    from sqlalchemy.orm import joinedload

    student_db_id = session["student_db_id"]
    today = get_today()
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
    student_db_id = session["student_db_id"]
    active_ban = StudentBan.query.filter(
        StudentBan.student_id == student_db_id,
        StudentBan.start_date <= get_today(),
        StudentBan.end_date >= get_today(),
    ).first()
    if active_ban:
        notif = {
            "error": "Anda sedang dalam masa larangan sampai {}. Alasan: {}".format(
                active_ban.end_date.strftime("%d/%m/%Y"), active_ban.reason
            )
        }
        return hx_render("siswa/beranda.jinja", **notif)

    min_date, max_date = _date_range()
    form = PermintaanSiswaForm()
    form.category_id.choices = _category_choices()
    form.reviewers.choices = _reviewer_choices()
    if request.method == "GET":
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=None,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
        )

    if not form.validate_on_submit():
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=None,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
        )

    notif = {}
    if form.date.data < min_date or form.date.data > max_date:
        notif["error"] = (
            "Tanggal harus dalam rentang hari ini sampai 7 hari ke depan"
        )
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=None,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
            **notif,
        )

    existing = BorrowingRequest.query.filter_by(
        student_id=student_db_id, date=form.date.data
    ).first()
    if existing:
        notif["error"] = (
            "Anda sudah mengajukan permintaan untuk tanggal tersebut"
        )
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=None,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
            **notif,
        )

    period = get_active_period_for(student_db_id, form.date.data)
    if period:
        notif["error"] = (
            "Tanggal tersebut sudah tercakup pinjaman periode {} s/d {} "
            "yang diberikan guru".format(
                period.start_date.strftime("%d/%m/%Y"),
                period.end_date.strftime("%d/%m/%Y"),
            )
        )
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=None,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
            **notif,
        )

    req = BorrowingRequest(
        student_id=student_db_id,
        category_id=form.category_id.data,
        date=form.date.data,
        status="pending",
        student_note=sanitize(form.student_note.data) or None,
        assigned_reviewers=[
            AssignedReviewer(teacher_id=tid) for tid in form.reviewers.data
        ],
    )
    db.session.add(req)
    db.session.commit()
    notif["success"] = "Permintaan peminjaman berhasil dibuat"
    return hx_render("siswa/beranda.jinja", push_url="siswa.beranda", **notif)


@bp.route("/permintaan/edit/<int:id>", methods=["GET", "POST"])
@login_required
def permintaan_edit(id):
    student_db_id = session["student_db_id"]
    active_ban = StudentBan.query.filter(
        StudentBan.student_id == student_db_id,
        StudentBan.start_date <= get_today(),
        StudentBan.end_date >= get_today(),
    ).first()
    if active_ban:
        notif = {
            "error": "Anda sedang dalam masa larangan sampai {}. Alasan: {}".format(
                active_ban.end_date.strftime("%d/%m/%Y"), active_ban.reason
            )
        }
        return hx_render("siswa/beranda.jinja", **notif)

    min_date, max_date = _date_range()
    req = db.get_or_404(BorrowingRequest, id)
    if req.student_id != student_db_id:
        return redirect(url_for("siswa.beranda"))
    if req.status != "pending":
        return redirect(url_for("siswa.beranda"))

    form = PermintaanSiswaForm(obj=req)
    form.category_id.choices = _category_choices()
    form.reviewers.choices = _reviewer_choices()
    if request.method == "GET":
        form.date.data = req.date
        form.category_id.data = req.category_id
        form.student_note.data = req.student_note
        form.reviewers.data = _saved_reviewers(form, req)
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=req,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
        )

    if not form.validate_on_submit():
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=req,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
        )

    notif = {}
    if form.date.data < min_date or form.date.data > max_date:
        notif["error"] = (
            "Tanggal harus dalam rentang hari ini sampai 7 hari ke depan"
        )
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=req,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
            **notif,
        )

    student_db_id = session["student_db_id"]
    existing = BorrowingRequest.query.filter(
        BorrowingRequest.student_id == student_db_id,
        BorrowingRequest.date == form.date.data,
        BorrowingRequest.id != id,
    ).first()
    if existing:
        notif["error"] = (
            "Anda sudah mengajukan permintaan untuk tanggal tersebut"
        )
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=req,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
            **notif,
        )

    period = get_active_period_for(student_db_id, form.date.data)
    if period and period.id != getattr(req, "loan_period_id", None):
        notif["error"] = (
            "Tanggal tersebut sudah tercakup pinjaman periode {} s/d {} "
            "yang diberikan guru".format(
                period.start_date.strftime("%d/%m/%Y"),
                period.end_date.strftime("%d/%m/%Y"),
            )
        )
        return hx_render(
            "siswa/permintaan_form.jinja",
            form=form,
            req=req,
            min_date=min_date.isoformat(),
            max_date=max_date.isoformat(),
            **notif,
        )

    req.category_id = form.category_id.data
    req.date = form.date.data
    req.student_note = sanitize(form.student_note.data) or None
    _sync_reviewers(req, form.reviewers.data)
    db.session.commit()
    notif["success"] = "Permintaan berhasil diperbarui"
    return hx_render("siswa/beranda.jinja", push_url="siswa.beranda", **notif)


def _sync_reviewers(req, teacher_ids):
    # Sinkron penunjukan pereview: hapus yang dicabut, tambah yang baru.
    # Replace koleksi sekaligus tidak bisa dipakai karena constraint
    # unik (request_id, teacher_id) — INSERT dieksekusi sebelum DELETE
    # lama saat flush bila pereview sama dipilih kembali.
    keep = list(dict.fromkeys(teacher_ids))  # dedupe, jaga urutan
    existing = {ar.teacher_id: ar for ar in req.assigned_reviewers}
    for tid in list(existing):
        if tid not in keep:
            db.session.delete(existing[tid])
    for tid in keep:
        if tid not in existing:
            req.assigned_reviewers.append(
                AssignedReviewer(teacher_id=tid)
            )


@bp.route("/permintaan/reviewer-pilihan")
@login_required
def reviewer_pilihan():
    # Fragment HTMX: render ulang pilihan guru pereview saat kategori
    # diganti. Preselect = guru pengawas kategori baru; jika kategori
    # sama dengan permintaan yang sedang diedit, pakai penunjukan
    # tersimpan supaya tidak hilang saat ganti-ganti kategori.
    category_id = request.args.get("category_id", type=int)
    req_id = request.args.get("req_id", type=int)

    form = PermintaanSiswaForm()
    form.reviewers.choices = _reviewer_choices()

    req = None
    if req_id:
        req = db.session.get(BorrowingRequest, req_id)
        if req and req.student_id != session["student_db_id"]:
            req = None

    selected = []
    if req and category_id == req.category_id:
        selected = _saved_reviewers(form, req)
    if not selected and category_id:
        selected = _category_default_reviewers(category_id)
    form.reviewers.data = selected

    return hx_render("siswa/_reviewer_field.jinja", form=form)


@bp.route("/permintaan/batal", methods=["POST"])
@login_required
def permintaan_batal():
    id = request.form.get("id", type=int)
    req = db.get_or_404(BorrowingRequest, id)
    notif = {}
    if req.student_id != session["student_db_id"]:
        notif["error"] = "Anda tidak berwenang membatalkan permintaan ini"
    elif req.status != "pending":
        notif["error"] = (
            "Hanya permintaan berstatus pending yang dapat dibatalkan"
        )
    else:
        db.session.delete(req)
        db.session.commit()
        notif["success"] = "Permintaan berhasil dibatalkan"
    return hx_render("siswa/beranda.jinja", push_url="siswa.beranda", **notif)


@bp.route("/permintaan/<int:id>")
@login_required
def permintaan_detail(id):
    from sqlalchemy.orm import joinedload

    req = db.get_or_404(
        BorrowingRequest,
        id,
        options=[
            joinedload(BorrowingRequest.category),
            joinedload(BorrowingRequest.reviewer),
        ],
    )

    if req.student_id != session["student_db_id"]:
        return redirect(url_for("siswa.beranda"))

    return hx_render("siswa/permintaan_detail.jinja", req=req)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_siswa"))
