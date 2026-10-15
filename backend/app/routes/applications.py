from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from ..auth import role_required
from ..extensions import db
from ..models import BeneficiaryApplication

applications = Blueprint("applications", __name__)
CONSENT_VERSION = "demo-local-v1"
TEXT_LIMITS = {"zone": 120, "availability": 300, "economic_context": 1000}
CHOICES = {
    "frequency": ("occasional", "weekly", "daily"),
    "transport": ("yes", "limited", "no"),
    "refrigeration": ("yes", "no"),
}


def own_application():
    return db.session.scalar(db.select(BeneficiaryApplication).where(
        BeneficiaryApplication.user_id == current_user.id))


def payload(allowed):
    data = request.get_json()
    if not isinstance(data, dict) or set(data) - allowed:
        abort(400, description="La petición contiene campos no permitidos.")
    if type(data.get("version")) is not int or data["version"] < 0:
        abort(400, description="Falta la versión de la solicitud. Recarga antes de continuar.")
    return data


def validate_answers(raw, submitting):
    allowed = set(TEXT_LIMITS) | set(CHOICES) | {"household_size"}
    if not isinstance(raw, dict) or set(raw) - allowed:
        abort(400, description="El formulario contiene campos no permitidos.")
    answers = {}
    for field, limit in TEXT_LIMITS.items():
        value = raw.get(field, "")
        if not isinstance(value, str) or len(value) > limit:
            abort(400, description=f"El campo {field} debe ser texto de hasta {limit} caracteres.")
        answers[field] = value.strip()
    for field, choices in CHOICES.items():
        value = raw.get(field, "")
        if not isinstance(value, str) or value not in ("", *choices):
            abort(400, description=f"Selecciona una opción válida para {field}.")
        answers[field] = value
    size = raw.get("household_size")
    if size is not None and (type(size) is not int or not 1 <= size <= 100):
        abort(400, description="El tamaño del hogar debe ser un entero entre 1 y 100, o quedar vacío.")
    answers["household_size"] = size
    if submitting and (not answers["zone"] or not answers["availability"]):
        abort(400, description="Para enviar, indica tu zona aproximada y disponibilidad de recogida.")
    return answers


def check_version(application, version):
    if version != (application.version if application else 0):
        abort(409, description="La solicitud cambió en otra pestaña. Recarga antes de editar.")
    if application and application.status not in ("draft", "pending", "information_requested"):
        abort(409, description="Esta solicitud ya fue revisada. La corrección requiere revisión humana.")


def commit():
    try:
        db.session.commit()
    except (IntegrityError, StaleDataError):
        db.session.rollback()
        abort(409, description="La solicitud cambió. Recarga antes de continuar.")


@applications.get("/applications/me")
@role_required("beneficiary")
def get_application():
    application = own_application()
    return jsonify(application=application.public_data() if application else None,
                   consent_version=CONSENT_VERSION)


@applications.post("/applications/me")
@role_required("beneficiary")
def save_application():
    data = payload({"answers", "consent", "consent_version", "action", "version"})
    if data.get("consent") is not True or data.get("consent_version") != CONSENT_VERSION:
        abort(400, description="Lee y acepta el consentimiento vigente antes de guardar.")
    if data.get("action") not in ("save", "submit"):
        abort(400, description="Selecciona guardar borrador o enviar solicitud.")
    answers = validate_answers(data.get("answers"), data["action"] == "submit")
    application = own_application()
    check_version(application, data["version"])
    now = datetime.now(timezone.utc)
    if application is None:
        application = BeneficiaryApplication(user_id=current_user.id)
        db.session.add(application)
    if application.consent_version != CONSENT_VERSION:
        application.consent_at = now
        application.consent_version = CONSENT_VERSION
    application.answers_json = answers
    application.updated_at = now
    application.status = "pending" if data["action"] == "submit" else "draft"
    application.submitted_at = now if data["action"] == "submit" else None
    commit()
    return jsonify(application=application.public_data())


@applications.delete("/applications/me")
@role_required("beneficiary")
def delete_application():
    data = payload({"version"})
    application = own_application()
    check_version(application, data["version"])
    if application:
        db.session.delete(application)
        commit()
    return "", 204
