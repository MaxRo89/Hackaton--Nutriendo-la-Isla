from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from ..extensions import db, login_manager
from ..models import User


@login_manager.user_loader
def load_user(token):
    return db.session.scalar(db.select(User).where(User.session_token == token)) if token else None


@login_manager.unauthorized_handler
def unauthorized():
    abort(401, description="Inicia sesión para continuar.")


def role_required(role, authorized_restaurant=False, approved_beneficiary=False):
    def decorate(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                abort(403, description="Tu cuenta no tiene acceso a esta función.")
            if authorized_restaurant and not current_user.restaurant_authorized:
                abort(403, description="Este restaurante aún no está autorizado.")
            if approved_beneficiary:
                from ..models import BeneficiaryApplication
                application = db.session.scalar(
                    db.select(BeneficiaryApplication).where(BeneficiaryApplication.user_id == current_user.id)
                )
                if application is None or application.status != "approved":
                    abort(403, description="Tu solicitud de acceso aún no ha sido aprobada.")
            return view(*args, **kwargs)
        return wrapped
    return decorate


approved_beneficiary_required = role_required("beneficiary", approved_beneficiary=True)
