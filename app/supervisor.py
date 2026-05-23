from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from .helper import WIB, admin_required, hx_render
from .models import BorrowingRequest, Student

bp = Blueprint("supervisor", __name__, url_prefix="/supervisor")


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
            }
        )
    return jsonify(data=data)
