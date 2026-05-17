from app import db

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(128))
    is_superadmin = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return '<Admin {}>'.format(self.username)


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(32), index=True, unique=True)
    name = db.Column(db.String(128))
    password = db.Column(db.String(128))
    class_id = db.Column(db.Integer)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    admin_note = db.Column(db.String(256))

    def __repr__(self):
        return '<Student {}>'.format(self.student_id)
