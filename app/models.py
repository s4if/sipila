from app import db

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(128))
    is_superadmin = db.Column(db.Boolean, nullable=False, default=False)
    name = db.Column(db.String(128))
    contact_person = db.Column(db.String(20))

    def __repr__(self):
        return '<Admin {}>'.format(self.username)


class ClassGroup(db.Model):
    __tablename__ = 'class_groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16), nullable=False)
    grade_level = db.Column(db.String(8), nullable=False)
    major = db.Column(db.String(64))
    homeroom_teacher_id = db.Column(db.Integer, db.ForeignKey('admins.id'))

    homeroom_teacher = db.relationship('Admin', backref='class_groups')
    students = db.relationship('Student', backref='class_group', lazy='select')

    @property
    def display_name(self):
        if self.major:
            return '{} {} {}'.format(self.grade_level, self.major, self.name)
        return '{} {}'.format(self.grade_level, self.name)
    
    @property
    def active_student_count(self):
        return Student.query.filter_by(class_group_id=self.id, is_deleted=False).count()

    def __repr__(self):
        return '<ClassGroup {}>'.format(self.display_name)


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(32), index=True, unique=True)
    name = db.Column(db.String(128))
    password = db.Column(db.String(128))
    class_group_id = db.Column(db.Integer, db.ForeignKey('class_groups.id'))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    admin_note = db.Column(db.String(256))

    def __repr__(self):
        return '<Student {}>'.format(self.student_id)
