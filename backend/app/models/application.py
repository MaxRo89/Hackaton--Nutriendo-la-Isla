from datetime import timezone

from ..extensions import db


def iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


class BeneficiaryApplication(db.Model):
    __tablename__ = "beneficiary_applications"
    __table_args__ = (db.CheckConstraint(
        "status IN ('draft', 'pending', 'information_requested', 'approved', 'rejected')",
        name="valid_application_status",
    ),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    answers_json = db.Column(db.JSON, nullable=False)
    consent_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consent_version = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="draft")
    submitted_at = db.Column(db.DateTime(timezone=True))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}
    reviews = db.relationship("ApplicationReview", cascade="all, delete-orphan", order_by="ApplicationReview.id")
    appeals = db.relationship("Appeal", cascade="all, delete-orphan", order_by="Appeal.id")

    def public_data(self):
        return {
            "id": self.id, "answers": self.answers_json, "status": self.status,
            "consent_at": iso(self.consent_at), "consent_version": self.consent_version,
            "submitted_at": iso(self.submitted_at), "updated_at": iso(self.updated_at),
            "version": self.version,
            "reviews": [review.public_data() for review in self.reviews],
            "appeals": [appeal.public_data() for appeal in self.appeals],
        }
