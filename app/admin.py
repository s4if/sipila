from flask import (
    Blueprint, make_response, render_template, request, session, url_for, redirect
)
from werkzeug.security import generate_password_hash, check_password_hash
from .db import db
from .helper import htmx, admin_required, sanitize_input
from .models import Admin, ClassGroup, Student

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@admin_required
def beranda():
    return render_template(
        'admin/beranda.jinja',
        admin_name=session['admin_name'],
        is_htmx=htmx,
    )

@bp.route('/ganti_password', methods=['GET', 'POST'])
@admin_required
def ganti_password():
    if request.method == 'GET':
        return render_template('admin/ganti_password.jinja', admin_name=session['admin_name'], is_htmx=htmx)

    notif = {}
    admin = Admin.query.filter_by(username=session['admin_name']).first()
    if request.form['new_password'] != request.form['confirm_password']:
        notif['error'] = 'Konfirmasi password tidak sesuai'
    elif admin and check_password_hash(admin.password, request.form['current_password']):
        admin.password = generate_password_hash(request.form['new_password'])
        db.session.commit()
        notif['success'] = 'Password berhasil diubah'
    else:
        notif['error'] = 'Password lama tidak sesuai'
    return render_template('admin/ganti_password.jinja', admin_name=session['admin_name'], is_htmx=htmx, **notif)

# ---- Rombel (ClassGroup) CRUD ----

@bp.route('/rombel')
@admin_required
def rombel():
    class_groups = ClassGroup.query.order_by(ClassGroup.id).all()
    return render_template(
        'admin/rombel.jinja',
        admin_name=session['admin_name'],
        is_htmx=htmx,
        class_groups=class_groups,
    )

@bp.route('/rombel/tambah', methods=['GET', 'POST'])
@admin_required
def rombel_tambah():
    admins = Admin.query.order_by(Admin.username).all()
    if request.method == 'GET':
        return render_template(
            'admin/rombel_form.jinja',
            admin_name=session['admin_name'],
            is_htmx=htmx,
            class_group=None,
            admins=admins,
        )

    notif = {}
    class_group = ClassGroup(
        name=sanitize_input(request.form['name']),
        grade_level=request.form['grade_level'],
        major=request.form.get('major') or None,
        homeroom_teacher_id=request.form.get('homeroom_teacher_id', type=int) or None,
    )
    db.session.add(class_group)
    db.session.commit()
    notif['success'] = 'Rombel berhasil ditambahkan'
    class_groups = ClassGroup.query.order_by(ClassGroup.id).all()
    response = make_response(render_template(
        'admin/rombel.jinja',
        admin_name=session['admin_name'],
        is_htmx=htmx,
        class_groups=class_groups,
        **notif,
    ))
    response.headers['HX-Push-Url'] = url_for('admin.rombel')
    return response

@bp.route('/rombel/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def rombel_edit(id):
    class_group = ClassGroup.query.get_or_404(id)
    admins = Admin.query.order_by(Admin.username).all()
    if request.method == 'GET':
        return render_template(
            'admin/rombel_form.jinja',
            admin_name=session['admin_name'],
            is_htmx=htmx,
            class_group=class_group,
            admins=admins,
        )

    notif = {}
    class_group.name = request.form['name']
    class_group.grade_level = request.form['grade_level']
    class_group.major = request.form.get('major') or None
    class_group.homeroom_teacher_id = request.form.get('homeroom_teacher_id', type=int) or None
    db.session.commit()
    notif['success'] = 'Rombel berhasil diperbarui'
    class_groups = ClassGroup.query.order_by(ClassGroup.id).all()
    response = make_response(render_template(
        'admin/rombel.jinja',
        admin_name=session['admin_name'],
        is_htmx=htmx,
        class_groups=class_groups,
        **notif,
    ))
    response.headers['HX-Push-Url'] = url_for('admin.rombel')
    return response

@bp.route('/rombel/hapus', methods=['POST'])
@admin_required
def rombel_hapus():
    id = request.form.get('id', type=int)
    class_group = ClassGroup.query.get_or_404(id)
    notif = {}
    active_students = Student.query.filter_by(class_group_id=id, is_deleted=False).first()
    if active_students:
        notif['error'] = 'Rombel tidak dapat dihapus karena masih memiliki siswa aktif'
    else:
        db.session.delete(class_group)
        db.session.commit()
        notif['success'] = 'Rombel berhasil dihapus'
    class_groups = ClassGroup.query.order_by(ClassGroup.id).all()
    response = make_response(render_template(
        'admin/rombel.jinja',
        admin_name=session['admin_name'],
        is_htmx=htmx,
        class_groups=class_groups,
        **notif,
    ))
    response.headers['HX-Push-Url'] = url_for('admin.rombel')
    return response

# ---- Siswa (Student) CRUD ----

@bp.route('/siswa')
@admin_required
def siswa():
    students = Student.query.filter_by(is_deleted=False).order_by(Student.id).all()
    return render_template(
        'admin/siswa.jinja',
        admin_name=session['admin_name'],
        is_htmx=htmx,
        students=students,
    )

@bp.route('/siswa/tambah', methods=['GET', 'POST'])
@admin_required
def siswa_tambah():
    class_groups = ClassGroup.query.order_by(ClassGroup.id).all()
    if request.method == 'GET':
        return render_template(
            'admin/siswa_form.jinja',
            admin_name=session['admin_name'],
            is_htmx=htmx,
            student=None,
            class_groups=class_groups,
        )

    notif = {}
    existing = Student.query.filter_by(student_id=request.form['student_id']).first()
    if existing:
        notif['error'] = 'NIS sudah terdaftar'
        return render_template(
            'admin/siswa_form.jinja',
            admin_name=session['admin_name'],
            is_htmx=htmx,
            student=None,
            class_groups=class_groups,
            **notif,
        )

    student = Student(
        student_id=sanitize_input(request.form['student_id']),
        name=sanitize_input(request.form['name']),
        password=generate_password_hash(request.form['password'], method='pbkdf2:sha256', salt_length=16),
        class_group_id=request.form.get('class_group_id', type=int),
        admin_note=sanitize_input(request.form.get('admin_note')),
    )
    db.session.add(student)
    db.session.commit()
    notif['success'] = 'Siswa berhasil ditambahkan'
    students = Student.query.filter_by(is_deleted=False).order_by(Student.id).all()
    response = make_response(render_template(
        'admin/siswa.jinja',
        admin_name=session['admin_name'],
        is_htmx=htmx,
        students=students,
        **notif,
    ))
    response.headers['HX-Push-Url'] = url_for('admin.siswa')
    return response

@bp.route('/siswa/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def siswa_edit(id):
    student = Student.query.get_or_404(id)
    class_groups = ClassGroup.query.order_by(ClassGroup.id).all()
    if request.method == 'GET':
        return render_template(
            'admin/siswa_form.jinja',
            admin_name=session['admin_name'],
            is_htmx=htmx,
            student=student,
            class_groups=class_groups,
        )

    notif = {}
    existing = Student.query.filter(
        Student.student_id == request.form['student_id'],
        Student.id != id,
    ).first()
    if existing:
        notif['error'] = 'NIS sudah digunakan siswa lain'
        return render_template(
            'admin/siswa_form.jinja',
            admin_name=session['admin_name'],
            is_htmx=htmx,
            student=student,
            class_groups=class_groups,
            **notif,
        )

    student.student_id = request.form['student_id']
    student.name = request.form['name']
    if request.form.get('password'):
        student.password = generate_password_hash(request.form['password'], method='pbkdf2:sha256', salt_length=16)
    student.class_group_id = request.form.get('class_group_id', type=int)
    student.admin_note = request.form.get('admin_note')
    db.session.commit()
    notif['success'] = 'Siswa berhasil diperbarui'
    students = Student.query.filter_by(is_deleted=False).order_by(Student.id).all()
    response = make_response(render_template(
        'admin/siswa.jinja',
        admin_name=session['admin_name'],
        is_htmx=htmx,
        students=students,
        **notif,
    ))
    response.headers['HX-Push-Url'] = url_for('admin.siswa')
    return response

@bp.route('/siswa/hapus', methods=['POST'])
@admin_required
def siswa_hapus():
    id = request.form.get('id', type=int)
    student = Student.query.get_or_404(id)
    student.is_deleted = True
    db.session.commit()
    notif = {'success': 'Siswa berhasil dihapus'}
    students = Student.query.filter_by(is_deleted=False).order_by(Student.id).all()
    response = make_response(render_template(
        'admin/siswa.jinja',
        admin_name=session['admin_name'],
        is_htmx=htmx,
        students=students,
        **notif,
    ))
    response.headers['HX-Push-Url'] = url_for('admin.siswa')
    return response
