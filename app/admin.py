from flask import (
    Blueprint, render_template, request, session, url_for, redirect
)
from .db import db
from .helper import htmx, admin_required

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
    from werkzeug.security import generate_password_hash, check_password_hash
    if request.method == 'GET':
        return render_template('admin/ganti_password.jinja', admin_name=session['admin_name'], is_htmx=htmx)

    notif = {}
    from .models import Admin
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
