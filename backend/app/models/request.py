from datetime import datetime, timezone

from ..extensions import db
from .application import iso


class DonationRequest(db.Model):
    __tablename__ = "donation_requests"
    __table_args__ = (
        db.CheckConstraint("quantity_milli > 0", name="positive_request_quantity"),
        db.CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'rejected')",
            name="valid_request_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.Integer, db.ForeignKey("donations.id"), nullable=False, index=True)
    beneficiary_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    quantity_milli = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    notes = db.Column(db.String(500), nullable=True)
    requested_at = db.Column(db.DateTime(timezone=True), nullable=False)
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}

    donation = db.relationship("Donation", back_populates="requests")
    beneficiary = db.relationship("User")

    def public_data(self):
        unit = self.donation.unit if self.donation else "unidad"
        return {
            "id": self.id,
            "donation_id": self.donation_id,
            "donation_title": self.donation.title if self.donation else "",
            "quantity": f"{self.quantity_milli // 1000}.{self.quantity_milli % 1000:03d}",
            "unit": unit,
            "status": self.status,
            "notes": self.notes,
            "pickup": self.donation.pickup_snapshot if self.donation else {},
            "requested_at": iso(self.requested_at),
            "confirmed_at": iso(self.confirmed_at),
            "cancelled_at": iso(self.cancelled_at),
            "version": self.version,
        }
