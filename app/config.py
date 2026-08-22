import os
import tomllib

basedir = os.path.abspath(os.path.dirname(__file__))
instancedir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../instance/")
)

if not os.path.isdir(instancedir):
    os.mkdir(instancedir)


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change-me-to-something-secret"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(instancedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Captcha gambar di halaman login (admin & siswa). Bisa dimatikan, mis.
    # saat testing, seperti WTF_CSRF_ENABLED.
    LOGIN_CAPTCHA_ENABLED = True


tomlfile = os.path.join(basedir, "../appconfig.toml")
with open(tomlfile, "rb") as f:
    APP_CONFIG = tomllib.load(f)
