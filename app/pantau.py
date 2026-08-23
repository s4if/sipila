# Monitor publik: halaman tanpa login untuk guru melihat sekilas semua
# permintaan peminjaman laptop hari ini (semua status).

from flask import Blueprint, jsonify, render_template

from .helper import get_today
from .models import BorrowingRequest, Student

bp = Blueprint("pantau", __name__)


@bp.route("/pantau")
def monitor():
    tanggal = get_today()
    return render_template(
        "pantau/monitor.jinja",
        tanggal=tanggal,
        tanggal_label=tanggal.strftime("%d/%m/%Y"),
    )


@bp.route("/pantau/data")
def monitor_data():
    from sqlalchemy.orm import joinedload

    # Selalu tampilkan hari ini; guru cukup memantau kondisi terkini.
    tanggal = get_today()

    requests = (
        BorrowingRequest.query.filter_by(date=tanggal)
        .options(
            joinedload(BorrowingRequest.student).joinedload(
                Student.class_group
            ),
            joinedload(BorrowingRequest.category),
        )
        .order_by(BorrowingRequest.id)
        .all()
    )

    status_badges = {
        "pending": '<span class="badge bg-warning text-dark">Pending</span>',
        "accepted": '<span class="badge bg-success">Diterima</span>',
        "rejected": '<span class="badge bg-danger">Ditolak</span>',
    }

    data = []
    for req in requests:
        student = req.student
        data.append(
            {
                "student_name": student.name if student else "-",
                "class_group": (
                    student.class_group.display_name
                    if student and student.class_group
                    else "-"
                ),
                "category": req.category.name if req.category else "-",
                "status": status_badges.get(req.status, req.status),
            }
        )
    return jsonify(data=data)
