from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, SelectMultipleField, StringField
from wtforms.validators import DataRequired, Optional


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class GuruForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    name = StringField("Nama", validators=[DataRequired()])
    contact_person = StringField("Kontak", validators=[Optional()])
    password = PasswordField("Password", validators=[Optional()])


class SiswaForm(FlaskForm):
    student_id = StringField("NIS", validators=[DataRequired()])
    name = StringField("Nama", validators=[DataRequired()])
    password = PasswordField("Password", validators=[Optional()])
    class_group_id = SelectField(
        "Rombel",
        coerce=lambda x: int(x) if x else None,
        validators=[DataRequired()],
    )
    admin_note = StringField("Catatan Admin", validators=[Optional()])


class RombelForm(FlaskForm):
    grade_level = SelectField(
        "Tingkat",
        choices=[
            ("", "Pilih tingkat"),
            ("X", "X"),
            ("XI", "XI"),
            ("XII", "XII"),
        ],
        validators=[DataRequired()],
    )
    major = SelectField(
        "Jurusan",
        choices=[("", "Tidak ada"), ("TJKT", "TJKT")],
        validators=[Optional()],
    )
    name = StringField("Nama / Nomor Rombel", validators=[DataRequired()])
    homeroom_teacher_id = SelectField(
        "Wali Kelas",
        coerce=lambda x: int(x) if x else None,
        validators=[Optional()],
    )


class KategoriForm(FlaskForm):
    name = StringField("Nama Kategori", validators=[DataRequired()])
    teachers = SelectMultipleField(
        "Guru Pengawas",
        coerce=int,
        validators=[Optional()],
    )
