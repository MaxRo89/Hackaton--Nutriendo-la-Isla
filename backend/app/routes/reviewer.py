from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify
from flask_login import current_user
from sqlalchemy import func

from ..auth import role_required
from ..extensions import db
from ..models import BeneficiaryApplication, ApplicationReview, Appeal, Donation, DonationRequest
from .applications import payload, commit, own_application

reviewer = Blueprint("reviewer", __name__)


def required_text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 1000:
        abort(400, description="Escribe un motivo o mensaje de entre 1 y 1000 caracteres.")
    return value.strip()


def version_matches(application, version):
    if application.version != version:
        abort(409, description="La solicitud cambió. Actualiza la página antes de continuar.")


@reviewer.get("/reviewer/applications")
@role_required("reviewer")
def list_applications():
    applications = db.session.scalars(db.select(BeneficiaryApplication).where(
        BeneficiaryApplication.status != "draft").order_by(BeneficiaryApplication.updated_at, BeneficiaryApplication.id)).all()
    return jsonify(applications=[application.public_data() for application in applications])


@reviewer.patch("/reviewer/applications/<int:application_id>")
@role_required("reviewer")
def decide(application_id):
    data = payload({"version", "decision", "reason"})
    if data.get("decision") not in ("approved", "rejected", "information_requested"):
        abort(400, description="Selecciona una decisión válida.")
    reason = required_text(data.get("reason"))
    application = db.get_or_404(BeneficiaryApplication, application_id)
    version_matches(application, data["version"])
    pending_appeals = [appeal for appeal in application.appeals if appeal.status == "pending"]
    if application.status != "pending" and not (application.status == "rejected" and pending_appeals):
        abort(409, description="Solo puedes revisar envíos pendientes o apelaciones pendientes.")
    now = datetime.now(timezone.utc)
    review = ApplicationReview(application_id=application.id, reviewer_id=current_user.id,
        application_version=application.version, decision=data["decision"], reason=reason, reviewed_at=now)
    db.session.add(review)
    application.status = data["decision"]
    application.updated_at = now
    for appeal in pending_appeals:
        appeal.status = "resolved"
        appeal.resolved_at = now
        appeal.resolution = review
    commit()
    return jsonify(application=application.public_data())


@reviewer.post("/applications/me/appeals")
@role_required("beneficiary")
def appeal():
    data = payload({"version", "message"})
    message = required_text(data.get("message"))
    application = own_application()
    if not application:
        abort(404, description="No tienes una solicitud que apelar.")
    version_matches(application, data["version"])
    if application.status != "rejected" or any(item.status == "pending" for item in application.appeals):
        abort(409, description="Solo puedes apelar una decisión no aprobada sin otra apelación pendiente.")
    now = datetime.now(timezone.utc)
    application.updated_at = now
    application.appeals.append(Appeal(message=message, created_at=now, status="pending"))
    commit()
    return jsonify(application=application.public_data()), 201


@reviewer.get("/reviewer/stats")
@role_required("reviewer")
def stats():
    """Aggregate metrics for the reviewer dashboard.

    Returns counts only — no individual beneficiary data is exposed.
    """
    # Application counts by status
    app_rows = db.session.execute(
        db.select(BeneficiaryApplication.status, func.count().label("n"))
        .group_by(BeneficiaryApplication.status)
    ).all()
    applications_by_status = {row.status: row.n for row in app_rows}

    # Donation counts by effective status
    now = datetime.now(timezone.utc)
    donation_rows = db.session.scalars(db.select(Donation)).all()
    donations_by_status: dict[str, int] = {}
    for d in donation_rows:
        s = d.public_data()["status"]
        donations_by_status[s] = donations_by_status.get(s, 0) + 1

    # Request counts by status
    req_rows = db.session.execute(
        db.select(DonationRequest.status, func.count().label("n"))
        .group_by(DonationRequest.status)
    ).all()
    requests_by_status = {row.status: row.n for row in req_rows}

    # Pending appeals count
    pending_appeals = db.session.scalar(
        db.select(func.count()).select_from(Appeal).where(Appeal.status == "pending")
    )

    return jsonify(
        applications=applications_by_status,
        donations=donations_by_status,
        requests=requests_by_status,
        pending_appeals=pending_appeals,
    )
