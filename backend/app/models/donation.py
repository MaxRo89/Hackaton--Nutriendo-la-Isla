from datetime import datetime, timezone

from ..extensions import db
from .application import iso


class RestaurantProfile(db.Model):
    __tablename__ = "restaurant_profiles"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    display_name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(200), nullable=False)
    pickup_label = db.Column(db.String(200), nullable=False)
    pickup_lat = db.Column(db.Float, nullable=False)
    pickup_lng = db.Column(db.Float, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}

    def public_data(self):
        return {key: getattr(self, key) for key in ('display_name', 'contact', 'pickup_label', 'pickup_lat', 'pickup_lng', 'version')}


class Donation(db.Model):
    __tablename__ = "donations"
    __table_args__ = (
        db.CheckConstraint("quantity_milli > 0", name="positive_donation_quantity"),
        db.CheckConstraint("unit IN ('pieza', 'porcion', 'kg')", name="valid_donation_unit"),
        db.CheckConstraint("status IN ('available', 'cancelled')", name="valid_donation_status"),
    )
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    quantity_milli = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(15), nullable=False)
    food_category = db.Column(db.String(30), nullable=False)
    allergens = db.Column(db.String(500), nullable=False)
    storage_notes = db.Column(db.String(500), nullable=False)
    handling_notes = db.Column(db.String(500), nullable=False)
    prepared_at = db.Column(db.DateTime(timezone=True))
    pickup_deadline = db.Column(db.DateTime(timezone=True), nullable=False)
    pickup_snapshot = db.Column(db.JSON, nullable=False)
    safety_confirmed_at = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="available")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}
    requests = db.relationship("DonationRequest", back_populates="donation", cascade="all, delete-orphan", order_by="DonationRequest.id")

    @property
    def confirmed_milli(self):
        return sum(req.quantity_milli for req in self.requests if req.status == 'confirmed')

    @property
    def remaining_milli(self):
        return max(0, self.quantity_milli - self.confirmed_milli)

    def public_data(self):
        result = {key: getattr(self, key) for key in ('id', 'title', 'description', 'unit', 'food_category', 'allergens', 'storage_notes', 'handling_notes', 'version')}
        effective_status = self.status
        if effective_status == 'available' and self.pickup_deadline.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            effective_status = 'expired'
        rem = self.remaining_milli
        if effective_status == 'available' and rem <= 0:
            effective_status = 'exhausted'
        result.update(quantity=f"{self.quantity_milli // 1000}.{self.quantity_milli % 1000:03d}",
                      remaining_quantity=f"{rem // 1000}.{rem % 1000:03d}",
                      status=effective_status, pickup=self.pickup_snapshot,
                      prepared_at=iso(self.prepared_at), pickup_deadline=iso(self.pickup_deadline),
                      created_at=iso(self.created_at), safety_confirmed_at=iso(self.safety_confirmed_at))
        return result
