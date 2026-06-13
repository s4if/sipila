from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, session

from .db import db
from .helper import WIB, admin_required, hx_render
from .models import BorrowingRequest, Student, Teacher

bp = Blueprint("supervisor", __name__, url_prefix="/supervisor")


def _get_current_teacher():
    return Teacher.query.filter_by(username=session.get("admin_name")).first()


@bp.route("/monitor")
@admin_required
def monitor():
    tanggal_str = request.args.get("tanggal")
    if tanggal_str:
        try:
            tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
        except ValueError:
            tanggal = datetime.now(WIB).date()
    else:
        tanggal = datetime.now(WIB).date()

    today = datetime.now(WIB).date()
    return hx_render(
        "supervisor/monitor.jinja",
        tanggal=tanggal,
        min_date=today - timedelta(days=365),
        max_date=today + timedelta(days=365),
    )


@bp.route("/monitor/data")
@admin_required
def monitor_data():
    from sqlalchemy.orm import joinedload

    tanggal_str = request.args.get("tanggal")
    if tanggal_str:
        try:
            tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
        except ValueError:
            tanggal = datetime.now(WIB).date()
    else:
        tanggal = datetime.now(WIB).date()

    requests = (
        BorrowingRequest.query.filter_by(status="accepted", date=tanggal)
        .options(
            joinedload(BorrowingRequest.student).joinedload(Student.class_group),
            joinedload(BorrowingRequest.category),
            joinedload(BorrowingRequest.reviewer),
            joinedload(BorrowingRequest.confirmer),
        )
        .order_by(BorrowingRequest.id)
        .all()
    )

    data = []
    for i, req in enumerate(requests, 1):
        student = req.student
        data.append(
            {
                "no": i,
                "request_id": req.id,
                "student_nis": student.student_id if student else "-",
                "student_name": student.name if student else "-",
                "class_group": (
                    student.class_group.display_name
                    if student and student.class_group
                    else "-"
                ),
                "category": req.category.name if req.category else "-",
                "student_note": req.student_note or "-",
                "reviewer": req.reviewer.name if req.reviewer else "-",
                "confirmation": req.confirmation,
                "confirmed_by": (
                    req.confirmer.name if req.confirmer else None
                ),
                "confirmed_at": (
                    req.confirmed_at.strftime("%d/%m/%Y %H:%M")
                    if req.confirmed_at
                    else None
                ),
            }
        )
    return jsonify(data=data)


@bp.route("/monitor/konfirmasi/<int:id>", methods=["POST"])
@admin_required
def monitor_konfirmasi(id):
    teacher = _get_current_teacher()
    if not teacher:
        return jsonify(success=False, message="Sesi tidak valid"), 403

    req = BorrowingRequest.query.get_or_404(id)

    if req.status != "accepted":
        return (
            jsonify(
                success=False, message="Hanya permintaan yang diterima dapat dikonfirmasi"
            ),
            400,
        )

    confirmation = request.form.get("confirmation")
    if confirmation not in ("used", "not_used"):
        return (
            jsonify(success=False, message="Nilai konfirmasi tidak valid"),
            400,
        )

    req.confirmation = confirmation
    req.confirmed_by = teacher.id
    req.confirmed_at = datetime.now(timezone.utc)
    db.session.commit()

    label = "digunakan" if confirmation == "used" else "tidak digunakan"
    return jsonify(success=True, message="Konfirmasi berhasil: {}".format(label))


@bp.route("/monitor/batalkan_konfirmasi/<int:id>", methods=["POST"])
@admin_required
def monitor_batalkan_konfirmasi(id):
    teacher = _get_current_teacher()
    if not teacher:
        return jsonify(success=False, message="Sesi tidak valid"), 403

    req = BorrowingRequest.query.get_or_404(id)

    if req.status != "accepted":
        return (
            jsonify(
                success=False, message="Hanya permintaan yang diterima dapat dikonfirmasi"
            ),
            400,
        )

    if not req.confirmation:
        return (
            jsonify(success=False, message="Permintaan belum dikonfirmasi"),
            400,
        )

    req.confirmation = None
    req.confirmed_by = None
    req.confirmed_at = None
    db.session.commit()

    return jsonify(success=True, message="Konfirmasi berhasil dibatalkan")
