from app import db

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(128))
    is_superadmin = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return '<Admin {}>'.format(self.username)
