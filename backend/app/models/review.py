from ..extensions import db
from .application import iso


class ApplicationReview(db.Model):
    __tablename__ = "application_reviews"
    __table_args__ = (db.CheckConstraint("decision IN ('approved', 'rejected', 'information_requested')", name="valid_review_decision"),)
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("beneficiary_applications.id"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    application_version = db.Column(db.Integer, nullable=False)
    decision = db.Column(db.String(30), nullable=False)
    reason = db.Column(db.String(1000), nullable=False)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=False)

    def public_data(self):
        return {"id": self.id, "decision": self.decision, "reason": self.reason,
                "reviewed_at": iso(self.reviewed_at)}


class Appeal(db.Model):
    __tablename__ = "appeals"
    __table_args__ = (db.CheckConstraint("status IN ('pending', 'resolved')", name="valid_appeal_status"),)
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("beneficiary_applications.id"), nullable=False)
    message = db.Column(db.String(1000), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True))
    resolution_review_id = db.Column(db.Integer, db.ForeignKey("application_reviews.id"))
    resolution = db.relationship("ApplicationReview")

    def public_data(self):
        return {"id": self.id, "message": self.message, "status": self.status,
                "created_at": iso(self.created_at), "resolved_at": iso(self.resolved_at),
                "resolution_review_id": self.resolution_review_id}
