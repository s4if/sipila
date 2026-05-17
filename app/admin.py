from flask import (
    Blueprint, make_response, render_template, request, session, url_for, redirect
)
from werkzeug.security import generate_password_hash, check_password_hash
from .db import db
from .helper import htmx, admin_required
from .models import Admin, Student

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
    if request.method == 'GET':
        return render_template(
            'admin/siswa_form.jinja',
            admin_name=session['admin_name'],
            is_htmx=htmx,
            student=None,
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
            **notif,
        )

    student = Student(
        student_id=request.form['student_id'],
        name=request.form['name'],
        password=generate_password_hash(request.form['password'], method='pbkdf2:sha256', salt_length=16),
        class_id=request.form.get('class_id', type=int),
        admin_note=request.form.get('admin_note'),
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
    if request.method == 'GET':
        return render_template(
            'admin/siswa_form.jinja',
            admin_name=session['admin_name'],
            is_htmx=htmx,
            student=student,
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
            **notif,
        )

    student.student_id = request.form['student_id']
    student.name = request.form['name']
    if request.form.get('password'):
        student.password = generate_password_hash(request.form['password'], method='pbkdf2:sha256', salt_length=16)
    student.class_id = request.form.get('class_id', type=int)
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
