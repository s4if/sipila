# Logika pinjaman periode (LoanPeriod): materialisasi malas row
# BorrowingRequest harian. Dipanggil dari hook before_request
# (permintaan hari ini dibuat di request pertama setiap hari — tanpa
# cron), saat guru membuat pinjaman periode baru yang mencakup hari
# ini, dan dari CLI command (backfill manual utk tanggal tertentu).

import logging
import threading

from .db import db
from .helper import get_today
from .models import (
    AssignedReviewer,
    BorrowingRequest,
    LoanPeriod,
    Student,
    StudentBan,
)

logger = logging.getLogger(__name__)

# Flag in-memory per proses: tanggal terakhir materialisasi malas yang
# berhasil dijalankan oleh proses ini.
_last_ensured_date = None
_ensure_lock = threading.Lock()


def ensure_today_materialized():
    # Materialisasi malas harian pengganti cron: dipanggil dari
    # before_request (lihat create_app). Flag in-memory membuat biaya
    # per request hanya perbandingan tanggal — setiap proses (gunicorn
    # worker) menjalankan materialisasi maksimal sekali per hari.
    # Kegagalan DB tidak diteruskan ke request; flag tidak di-set
    # sehingga otomatis dicoba lagi di request berikutnya.
    global _last_ensured_date
    today = get_today()
    if _last_ensured_date == today:
        return
    with _ensure_lock:
        if _last_ensured_date == today:
            return
        try:
            materialize_periods(today)
            _last_ensured_date = today
        except Exception:
            db.session.rollback()
            logger.exception(
                "Materialisasi pinjaman periode harian gagal, "
                "akan dicoba lagi di request berikutnya"
            )


def get_active_period_for(student_id, target_date):
    # Cari LoanPeriod aktif milik siswa yang mencakup target_date
    return LoanPeriod.query.filter(
        LoanPeriod.is_active.is_(True),
        LoanPeriod.student_id == student_id,
        LoanPeriod.start_date <= target_date,
        LoanPeriod.end_date >= target_date,
    ).first()


def materialize_periods(target_date=None):
    # Buat row BorrowingRequest utk semua LoanPeriod aktif yang mencakup
    # target_date (default: hari ini). Idempotent — tanggal yang sudah
    # punya request (termasuk permintaan manual siswa) tidak ditimpa.
    # Hari ketika siswa kena larangan (StudentBan) dilewati.
    # Return jumlah row yang dibuat.
    if target_date is None:
        target_date = get_today()

    periods = (
        LoanPeriod.query.join(Student, LoanPeriod.student_id == Student.id)
        .filter(
            LoanPeriod.is_active.is_(True),
            Student.is_deleted.is_(False),
            LoanPeriod.start_date <= target_date,
            LoanPeriod.end_date >= target_date,
        )
        .all()
    )

    created = 0
    for period in periods:
        banned = StudentBan.query.filter(
            StudentBan.student_id == period.student_id,
            StudentBan.start_date <= target_date,
            StudentBan.end_date >= target_date,
        ).first()
        if banned:
            continue

        exists = BorrowingRequest.query.filter_by(
            student_id=period.student_id, date=target_date
        ).first()
        if exists:
            continue

        db.session.add(
            BorrowingRequest(
                student_id=period.student_id,
                category_id=period.category_id,
                date=target_date,
                status="accepted",
                reviewed_by=period.created_by,
                teacher_note=period.note,
                reviewed_at=period.created_at,
                loan_period_id=period.id,
                # Guru pemberi izin dicatat sebagai pereview agar tetap
                # terlihat di daftar permintaan miliknya
                assigned_reviewers=[
                    AssignedReviewer(teacher_id=period.created_by)
                ],
            )
        )
        created += 1

    db.session.commit()
    return created
