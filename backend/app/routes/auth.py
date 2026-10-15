import re
import secrets

from flask import Blueprint, abort, jsonify, request, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth import role_required
from ..extensions import db
from ..models import User

auth = Blueprint("auth", __name__)
# Equal-cost password check for unknown accounts; contains no real credential.
DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32), method="scrypt")


def credentials(register=False):
    data = request.get_json()
    if not isinstance(data, dict):
        abort(400, description="Envía un objeto JSON válido.")
    allowed = {"email", "password", "role"} if register else {"email", "password"}
    if set(data) - allowed:
        abort(400, description="La petición contiene campos no permitidos.")
    email, password = data.get("email"), data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        abort(400, description="Correo y contraseña son obligatorios.")
    email = email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        abort(400, description="Introduce un correo válido.")
    if not 12 <= len(password) <= 128:
        abort(400, description="La contraseña debe tener entre 12 y 128 caracteres.")
    return data, email, password


def start_session(user):
    session.clear()
    user.session_token = secrets.token_hex(32)
    db.session.commit()
    login_user(user, remember=False)
    session.permanent = True


@auth.get("/auth/csrf")
def csrf_token():
    return jsonify(csrf_token=generate_csrf())


@auth.post("/auth/register")
def register():
    if current_user.is_authenticated:
        abort(409, description="Cierra tu sesión antes de crear otra cuenta.")
    data, email, password = credentials(register=True)
    if data.get("role") not in ("restaurant", "beneficiary"):
        abort(400, description="Selecciona restaurante o beneficiario.")
    user = User(email=email, role=data["role"], restaurant_authorized=False)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Ya existe una cuenta con ese correo.")
    start_session(user)
    return jsonify(user=user.public_data()), 201


@auth.post("/auth/login")
def login():
    if current_user.is_authenticated:
        abort(409, description="Cierra tu sesión antes de cambiar de cuenta.")
    _, email, password = credentials()
    user = db.session.scalar(db.select(User).where(User.email == email))
    valid = check_password_hash(user.password_hash if user else DUMMY_HASH, password)
    if not user or not valid:
        abort(401, description="Correo o contraseña incorrectos.")
    start_session(user)
    return jsonify(user=user.public_data())


@auth.get("/auth/me")
@login_required
def me():
    return jsonify(user=current_user.public_data())


@auth.post("/auth/logout")
@login_required
def logout():
    current_user.session_token = None
    db.session.commit()
    logout_user()
    session.clear()
    return "", 204


@auth.get("/restaurant/access")
@role_required("restaurant", authorized_restaurant=True)
def restaurant_access():
    return jsonify(message="Restaurante ficticio autorizado. Completa tu perfil y publica excedentes de demostración.")


@auth.get("/beneficiary/access")
@role_required("beneficiary")
def beneficiary_access():
    return jsonify(message="Completa tu solicitud y consulta su estado. Enviarla no habilita acceso a donaciones: requiere revisión humana.")


@auth.get("/reviewer/access")
@role_required("reviewer")
def reviewer_access():
    return jsonify(message="Revisa solicitudes y apelaciones. Toda decisión requiere un motivo visible para la persona solicitante.")
