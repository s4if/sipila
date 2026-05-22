from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .db import db
from .forms import RombelForm, SiswaForm
from .helper import admin_required, hx_render, sanitize_input
from .models import Admin, ClassGroup, Student

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def beranda():
    return hx_render("admin/beranda.jinja")


@bp.route("/ganti_password", methods=["GET", "POST"])
@admin_required
def ganti_password():
    if request.method == "GET":
        return hx_render("admin/ganti_password.jinja")

    notif = {}
    admin = Admin.query.filter_by(username=session["admin_name"]).first()
    if request.form["new_password"] != request.form["confirm_password"]:
        notif["error"] = "Konfirmasi password tidak sesuai"
    elif admin and check_password_hash(
        admin.password, request.form["current_password"]
    ):
        admin.password = generate_password_hash(request.form["new_password"])
        db.session.commit()
        notif["success"] = "Password berhasil diubah"
    else:
        notif["error"] = "Password lama tidak sesuai"
    return hx_render("admin/ganti_password.jinja", **notif)


# ---- Rombel (ClassGroup) CRUD ----


@bp.route("/rombel")
@admin_required
def rombel():
    return hx_render("admin/rombel.jinja")


@bp.route("/rombel/data")
@admin_required
def rombel_data():
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload

    class_groups = (
        ClassGroup.query.options(joinedload(ClassGroup.homeroom_teacher))
        .order_by(ClassGroup.id)
        .all()
    )

    active_counts = dict(
        db.session.query(Student.class_group_id, func.count(Student.id))
        .filter(~Student.is_deleted, Student.class_group_id.isnot(None))
        .group_by(Student.class_group_id)
        .all()
    )

    data = []
    for i, cg in enumerate(class_groups, 1):
        guru = (
            (cg.homeroom_teacher.name or "[nama belum di set]")
            if cg.homeroom_teacher
            else "-"
        )
        data.append(
            {
                "no": i,
                "display_name": cg.display_name,
                "grade_level": cg.grade_level,
                "major": cg.major or "-",
                "homeroom_teacher": guru,
                "student_count": active_counts.get(cg.id, 0),
                "actions": (
                    '<a class="btn btn-sm btn-warning" '
                    f'onclick="edit_rombel({cg.id})">'
                    '<i class="bi bi-pencil"></i> Edit</a> '
                    '<button type="button" class="btn btn-sm btn-danger" '
                    f"onclick=\"hapus_rombel({cg.id}, '{sanitize_input(cg.display_name)}')\">"
                    '<i class="bi bi-trash"></i> Hapus</button>'
                ),
            }
        )
    return jsonify(data=data)


@bp.route("/rombel/tambah", methods=["GET", "POST"])
@admin_required
def rombel_tambah():
    form = RombelForm()
    form.homeroom_teacher_id.choices = [("", "Belum ditentukan")] + [
        (a.id, a.name or "[nama belum di set]")
        for a in Admin.query.order_by(Admin.username).all()
    ]
    if request.method == "GET":
        return hx_render(
            "admin/rombel_form.jinja", class_group=None, form=form
        )

    if not form.validate_on_submit():
        return hx_render(
            "admin/rombel_form.jinja", class_group=None, form=form
        )

    notif = {}
    class_group = ClassGroup(
        name=sanitize_input(form.name.data),
        grade_level=form.grade_level.data,
        major=form.major.data or None,
        homeroom_teacher_id=form.homeroom_teacher_id.data or None,
    )
    db.session.add(class_group)
    db.session.commit()
    notif["success"] = "Rombel berhasil ditambahkan"
    return hx_render("admin/rombel.jinja", push_url="admin.rombel", **notif)


@bp.route("/rombel/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def rombel_edit(id):
    class_group = ClassGroup.query.get_or_404(id)
    form = RombelForm(obj=class_group)
    form.homeroom_teacher_id.choices = [("", "Belum ditentukan")] + [
        (a.id, a.name or "[nama belum di set]")
        for a in Admin.query.order_by(Admin.username).all()
    ]
    if request.method == "GET":
        return hx_render(
            "admin/rombel_form.jinja", class_group=class_group, form=form
        )

    if not form.validate_on_submit():
        return hx_render(
            "admin/rombel_form.jinja", class_group=class_group, form=form
        )

    notif = {}
    class_group.name = form.name.data
    class_group.grade_level = form.grade_level.data
    class_group.major = form.major.data or None
    class_group.homeroom_teacher_id = form.homeroom_teacher_id.data or None
    db.session.commit()
    notif["success"] = "Rombel berhasil diperbarui"
    return hx_render("admin/rombel.jinja", push_url="admin.rombel", **notif)


@bp.route("/rombel/hapus", methods=["POST"])
@admin_required
def rombel_hapus():
    id = request.form.get("id", type=int)
    class_group = ClassGroup.query.get_or_404(id)
    notif = {}
    active_students = Student.query.filter_by(
        class_group_id=id, is_deleted=False
    ).first()
    if active_students:
        notif["error"] = (
            "Rombel tidak dapat dihapus karena masih memiliki siswa aktif"
        )
    else:
        db.session.delete(class_group)
        db.session.commit()
        notif["success"] = "Rombel berhasil dihapus"
    return hx_render("admin/rombel.jinja", push_url="admin.rombel", **notif)


# ---- Siswa (Student) CRUD ----


@bp.route("/siswa")
@admin_required
def siswa():
    return hx_render("admin/siswa.jinja")


@bp.route("/siswa/data")
@admin_required
def siswa_data():
    from sqlalchemy.orm import joinedload

    students = (
        Student.query.filter_by(is_deleted=False)
        .options(joinedload(Student.class_group))
        .order_by(Student.id)
        .all()
    )
    data = []
    for i, student in enumerate(students, 1):
        data.append(
            {
                "no": i,
                "student_id": student.student_id,
                "name": student.name,
                "class_group": student.class_group.display_name
                if student.class_group
                else "-",
                "admin_note": student.admin_note or "",
                "actions": (
                    '<a class="btn btn-sm btn-warning" '
                    f'onclick="edit_siswa({student.id})">'
                    '<i class="bi bi-pencil"></i> Edit</a> '
                    '<button type="button" class="btn btn-sm btn-danger" '
                    f"onclick=\"hapus_siswa({student.id}, '{sanitize_input(student.name)}')\">"
                    '<i class="bi bi-trash"></i> Hapus</button>'
                ),
            }
        )
    return jsonify(data=data)


@bp.route("/siswa/tambah", methods=["GET", "POST"])
@admin_required
def siswa_tambah():
    form = SiswaForm()
    form.class_group_id.choices = [("", "Pilih rombel")] + [
        (cg.id, cg.display_name) for cg in ClassGroup.query.order_by(ClassGroup.id).all()
    ]
    if request.method == "GET":
        return hx_render(
            "admin/siswa_form.jinja", student=None, form=form
        )

    if not form.validate_on_submit():
        return hx_render(
            "admin/siswa_form.jinja", student=None, form=form
        )

    notif = {}
    existing = Student.query.filter_by(
        student_id=form.student_id.data
    ).first()
    if existing:
        notif["error"] = "NIS sudah terdaftar"
        return hx_render(
            "admin/siswa_form.jinja",
            student=None,
            form=form,
            **notif,
        )

    if not form.password.data:
        form.password.errors.append("Password wajib diisi")
        return hx_render(
            "admin/siswa_form.jinja", student=None, form=form
        )

    student = Student(
        student_id=sanitize_input(form.student_id.data),
        name=sanitize_input(form.name.data),
        password=generate_password_hash(
            form.password.data, method="pbkdf2:sha256", salt_length=16
        ),
        class_group_id=form.class_group_id.data,
        admin_note=sanitize_input(form.admin_note.data),
    )
    db.session.add(student)
    db.session.commit()
    notif["success"] = "Siswa berhasil ditambahkan"
    return hx_render("admin/siswa.jinja", push_url="admin.siswa", **notif)


@bp.route("/siswa/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def siswa_edit(id):
    student = Student.query.get_or_404(id)
    form = SiswaForm(obj=student)
    form.class_group_id.choices = [("", "Pilih rombel")] + [
        (cg.id, cg.display_name) for cg in ClassGroup.query.order_by(ClassGroup.id).all()
    ]
    if request.method == "GET":
        return hx_render(
            "admin/siswa_form.jinja", student=student, form=form
        )

    if not form.validate_on_submit():
        return hx_render(
            "admin/siswa_form.jinja", student=student, form=form
        )

    notif = {}
    existing = Student.query.filter(
        Student.student_id == form.student_id.data,
        Student.id != id,
    ).first()
    if existing:
        notif["error"] = "NIS sudah digunakan siswa lain"
        return hx_render(
            "admin/siswa_form.jinja",
            student=student,
            form=form,
            **notif,
        )

    student.student_id = form.student_id.data
    student.name = form.name.data
    if form.password.data:
        student.password = generate_password_hash(
            form.password.data, method="pbkdf2:sha256", salt_length=16
        )
    student.class_group_id = form.class_group_id.data
    student.admin_note = form.admin_note.data
    db.session.commit()
    notif["success"] = "Siswa berhasil diperbarui"
    return hx_render("admin/siswa.jinja", push_url="admin.siswa", **notif)


@bp.route("/siswa/hapus", methods=["POST"])
@admin_required
def siswa_hapus():
    id = request.form.get("id", type=int)
    student = Student.query.get_or_404(id)
    student.is_deleted = True
    db.session.commit()
    notif = {"success": "Siswa berhasil dihapus"}
    return hx_render("admin/siswa.jinja", push_url="admin.siswa", **notif)
