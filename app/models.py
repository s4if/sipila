from app import db
from app.helper import get_now, get_today


class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(128))
    is_superadmin = db.Column(db.Boolean, nullable=False, default=False)
    # Soft delete: guru terhapus tetap tersimpan (riwayat review/larangan
    # tetap merujuk id-nya) tapi tidak bisa login dan tidak muncul di UI.
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    name = db.Column(db.String(128))
    contact_person = db.Column(db.String(20))

    def __repr__(self):
        return "<Teacher {}>".format(self.username)


class ClassGroup(db.Model):
    __tablename__ = "class_groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16), nullable=False)
    grade_level = db.Column(db.String(8), nullable=False)
    major = db.Column(db.String(64))
    homeroom_teacher_id = db.Column(
        db.Integer, db.ForeignKey("teachers.id")
    )

    homeroom_teacher = db.relationship("Teacher", backref="class_groups")
    students = db.relationship("Student", backref="class_group", lazy="select")

    @property
    def display_name(self):
        if self.major:
            return "{} {} {}".format(self.grade_level, self.major, self.name)
        return "{} {}".format(self.grade_level, self.name)

    @property
    def active_student_count(self):
        return Student.query.filter_by(
            class_group_id=self.id, is_deleted=False
        ).count()

    def __repr__(self):
        return "<ClassGroup {}>".format(self.display_name)


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(32), index=True, unique=True)
    name = db.Column(db.String(128))
    password = db.Column(db.String(128))
    class_group_id = db.Column(
        db.Integer, db.ForeignKey("class_groups.id"), index=True
    )
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    admin_note = db.Column(db.String(256))

    def __repr__(self):
        return "<Student {}>".format(self.student_id)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    # Soft delete: saat dihapus, name diganti "[deleted]" dan link guru
    # pengawas dibersihkan; riwayat permintaan tetap merujuk row ini.
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    teacher_links = db.relationship(
        "CategoryTeacher",
        backref="category",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return "<Category {}>".format(self.name)


class CategoryTeacher(db.Model):
    __tablename__ = "category_teachers"
    __table_args__ = (db.UniqueConstraint("category_id", "teacher_id"),)
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=False
    )
    teacher_id = db.Column(
        db.Integer, db.ForeignKey("teachers.id"), nullable=False, index=True
    )

    def __repr__(self):
        return "<CategoryTeacher cat={} teacher={}>".format(
            self.category_id, self.teacher_id
        )


class StudentBan(db.Model):
    __tablename__ = "student_bans"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False,
        index=True,
    )
    creator_id = db.Column(
        db.Integer, db.ForeignKey("teachers.id"), nullable=False
    )
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(256), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=get_now
    )

    student = db.relationship("Student", backref=db.backref("bans", lazy="dynamic"))
    creator = db.relationship("Teacher", backref="created_bans")

    def __repr__(self):
        return "<StudentBan student_id={} start={} end={}>".format(
            self.student_id, self.start_date, self.end_date
        )

    @property
    def is_active(self):
        return self.start_date <= get_today() <= self.end_date

    @property
    def is_concluded(self):
        return self.end_date < get_today()


class LoanPeriod(db.Model):
    # Pinjaman jangka panjang yang diberikan guru. Row BorrowingRequest
    # harian di-generate malas (lazy) dari sini, satu per satu saat
    # tanggalnya tiba (lihat app/periods.py).
    __tablename__ = "loan_periods"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False,
        index=True,
    )
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=False,
        index=True,
    )
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("teachers.id"), nullable=False
    )
    created_at = db.Column(
        db.DateTime, nullable=False, default=get_now
    )
    cancelled_at = db.Column(db.DateTime, nullable=True)

    student = db.relationship("Student", backref="loan_periods")
    category = db.relationship("Category", backref="loan_periods")
    creator = db.relationship("Teacher", backref="loan_periods")
    requests = db.relationship(
        "BorrowingRequest",
        backref="loan_period",
        lazy="dynamic",
        passive_deletes=True,
    )

    def __repr__(self):
        return "<LoanPeriod student={} {} s/d {} active={}>".format(
            self.student_id, self.start_date, self.end_date, self.is_active
        )

    @property
    def status_label(self):
        # Dipakai template untuk badge: active/upcoming/concluded/cancelled
        if not self.is_active:
            return "cancelled"
        if self.end_date < get_today():
            return "concluded"
        if self.start_date > get_today():
            return "upcoming"
        return "active"


class BorrowingRequest(db.Model):
    __tablename__ = "borrowing_requests"
    __table_args__ = (db.UniqueConstraint("student_id", "date"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False
    )
    # Kategori opsional: sejak penunjukan pereview dipindah ke
    # AssignedReviewer, kategori hanya informatif (laporan + preselect
    # guru pereview) sehingga boleh kosong.
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=True
    )
    # Terisi jika row ini digenerate dari LoanPeriod (izin panjang).
    # Saat LoanPeriod dihapus, FK ini di-set NULL oleh DB (ON DELETE SET
    # NULL, lihat pragma foreign_keys di app/db.py) — riwayat permintaan
    # tetap tersimpan tanpa terkait izin lagi.
    loan_period_id = db.Column(
        db.Integer,
        db.ForeignKey("loan_periods.id", ondelete="SET NULL"),
        nullable=True,
    )
    date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(
        db.String(16), nullable=False, default="pending", index=True
    )
    reviewed_by = db.Column(
        db.Integer, db.ForeignKey("teachers.id"), nullable=True
    )
    student_note = db.Column(db.String(256), nullable=True)
    teacher_note = db.Column(db.String(256), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=get_now
    )
    reviewed_at = db.Column(db.DateTime, nullable=True)
    confirmation = db.Column(db.String(16), nullable=True)
    confirmed_by = db.Column(
        db.Integer, db.ForeignKey("teachers.id"), nullable=True
    )
    confirmed_at = db.Column(db.DateTime, nullable=True)

    student = db.relationship("Student", backref="borrowing_requests")
    category = db.relationship("Category", backref="borrowing_requests")
    reviewer = db.relationship(
        "Teacher",
        foreign_keys=[reviewed_by],
        backref="reviewed_requests",
    )
    confirmer = db.relationship(
        "Teacher",
        foreign_keys=[confirmed_by],
        backref="confirmed_requests",
    )

    def __repr__(self):
        return "<BorrowingRequest student={} date={} status={}>".format(
            self.student_id, self.date, self.status
        )

class AssignedReviewer(db.Model):
    # Penunjukan guru pereview per permintaan. Awalnya di-preselect dari
    # guru pengawas kategori (CategoryTeacher), tapi siswa boleh mengubah
    # pilihannya; hanya guru pada tabel ini yang boleh menyetujui
    # BorrowingRequest terkait (menggantikan aturan berbasis kategori).
    __tablename__ = "assigned_reviewers"
    __table_args__ = (db.UniqueConstraint("request_id", "teacher_id"),)
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.Integer,
        db.ForeignKey("borrowing_requests.id"),
        nullable=False,
        index=True,
    )
    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id"),
        nullable=False,
        index=True,
    )
    assigned_at = db.Column(
        db.DateTime, nullable=False, default=get_now
    )

    # Saat permintaan dihapus (mis. dibatalkan siswa), baris penunjukan
    # ikut dihapus; riwayat tetap merujuk teacher_id yang soft-delete.
    request = db.relationship(
        "BorrowingRequest",
        backref=db.backref(
            "assigned_reviewers", cascade="all, delete-orphan"
        ),
    )
    teacher = db.relationship("Teacher", backref="assigned_reviews")

    def __repr__(self):
        return "<AssignedReviewer request={} teacher={}>".format(
            self.request_id, self.teacher_id
        )
