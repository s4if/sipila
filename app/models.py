from datetime import datetime, timezone

from app import db


class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(128))
    is_superadmin = db.Column(db.Boolean, nullable=False, default=False)
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
    homeroom_teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))

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
    class_group_id = db.Column(db.Integer, db.ForeignKey("class_groups.id"))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    admin_note = db.Column(db.String(256))

    def __repr__(self):
        return "<Student {}>".format(self.student_id)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)

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
        db.Integer, db.ForeignKey("teachers.id"), nullable=False
    )

    def __repr__(self):
        return "<CategoryTeacher cat={} teacher={}>".format(
            self.category_id, self.teacher_id
        )


class BorrowingRequest(db.Model):
    __tablename__ = "borrowing_requests"
    __table_args__ = (db.UniqueConstraint("student_id", "date"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False
    )
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=False
    )
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending")
    reviewed_by = db.Column(
        db.Integer, db.ForeignKey("teachers.id"), nullable=True
    )
    student_note = db.Column(db.String(256), nullable=True)
    teacher_note = db.Column(db.String(256), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
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
