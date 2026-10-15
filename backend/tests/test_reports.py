"""Phase 8 — Integration tests: stats endpoint and full end-to-end demo cycle."""
from datetime import datetime, timedelta, timezone
import pytest

from test_auth import app, post, register
from test_donations import restaurant, profile, publish, make_beneficiary
from app.extensions import db
from app.models import Donation, DonationRequest, BeneficiaryApplication


# ── Helper ─────────────────────────────────────────────────────────────────

def make_reviewer(app_fixture):
    """Create a reviewer account directly (reviewers cannot self-register via public API)."""
    email = f"rev-{id(app_fixture)}@demo.invalid"
    with app_fixture.app_context():
        from app.models import User
        user = db.session.scalar(db.select(User).where(User.email == email))
        if user is None:
            user = User(email=email, role="reviewer")
            user.set_password("ReviewerPass123!")
            db.session.add(user)
            db.session.commit()
    client = app_fixture.test_client()
    from test_auth import post
    login = post(client, "/api/auth/login", {"email": email, "password": "ReviewerPass123!"})
    assert login.status_code == 200, f"Reviewer login failed: {login.data}"
    return client


# ── Reviewer stats endpoint ─────────────────────────────────────────────────

def test_stats_requires_reviewer(app, restaurant):
    """Only reviewers can access /reviewer/stats."""
    anon = app.test_client()
    assert anon.get("/api/reviewer/stats").status_code == 401

    ben = make_beneficiary(app, status="approved", email="stats-ben@demo.invalid")
    assert ben.get("/api/reviewer/stats").status_code == 403

    profile(restaurant)
    assert restaurant.get("/api/reviewer/stats").status_code == 403


def test_stats_returns_aggregate_counts(app, restaurant):
    """Stats returns counts by status without individual data."""
    rev = make_reviewer(app)

    # Baseline — no donations yet
    data = rev.get("/api/reviewer/stats").json
    assert "applications" in data
    assert "donations" in data
    assert "requests" in data
    assert "pending_appeals" in data
    # No individual emails, names, or answers exposed
    for key in ("email", "answers", "name"):
        assert key not in str(data)

    # Add some state
    profile(restaurant)
    d = publish(restaurant, quantity="5", unit="pieza").json["donation"]
    ben = make_beneficiary(app, status="approved", email="stats-ben2@demo.invalid")
    post(ben, f"/api/donations/{d['id']}/requests", {"quantity": "2"})

    data2 = rev.get("/api/reviewer/stats").json
    # Donations available count increased
    assert data2["donations"].get("available", 0) >= 1
    # Pending requests count
    assert data2["requests"].get("pending", 0) >= 1
    # Applications approved count
    assert data2["applications"].get("approved", 0) >= 1


def test_stats_counts_all_application_statuses(app):
    """Stats correctly tallies each application status."""
    rev = make_reviewer(app)

    # Create beneficiaries with different statuses
    make_beneficiary(app, status="pending", email="stp1@demo.invalid")
    make_beneficiary(app, status="approved", email="stp2@demo.invalid")
    make_beneficiary(app, status="rejected", email="stp3@demo.invalid")

    data = rev.get("/api/reviewer/stats").json
    apps = data["applications"]
    assert apps.get("approved", 0) >= 1
    assert apps.get("pending", 0) >= 1
    assert apps.get("rejected", 0) >= 1


# ── Full end-to-end cycle ──────────────────────────────────────────────────

def test_full_mvp_cycle(app, restaurant):
    """Full cycle: publish → list on map → request → confirm → history.

    Validates the complete MVP flow described in the README phase-7 section.
    """
    # 1. Restaurant sets profile and publishes
    profile(restaurant)
    pub = publish(restaurant, quantity="10", unit="pieza")
    assert pub.status_code == 201
    d = pub.json["donation"]
    assert d["status"] == "available"
    assert d["pickup"]["pickup_lat"] == 18.65

    # 2. Approved beneficiary sees donation in list and map endpoint
    ben = make_beneficiary(app, status="approved", email="e2e-ben@demo.invalid")
    listing = ben.get("/api/donations").json["donations"]
    assert any(item["id"] == d["id"] for item in listing)

    detail = ben.get(f"/api/donations/{d['id']}").json["donation"]
    assert detail["id"] == d["id"]
    assert detail["status"] == "available"
    assert "pickup_lat" in detail["pickup"]

    # 3. Non-approved beneficiary cannot see donations
    unapproved = make_beneficiary(app, status="pending", email="e2e-unapp@demo.invalid")
    assert unapproved.get("/api/donations").status_code == 403

    # 4. Beneficiary requests a partial quantity with notes
    req_res = post(ben, f"/api/donations/{d['id']}/requests", {
        "quantity": "3",
        "notes": "Paso hoy a las 5:00 PM",
    })
    assert req_res.status_code == 201
    req = req_res.json["request"]
    assert req["status"] == "pending"
    assert req["quantity"] == "3.000"
    assert req["notes"] == "Paso hoy a las 5:00 PM"

    # 5. Beneficiary views own requests
    my_reqs = ben.get("/api/beneficiary/requests").json["requests"]
    assert any(r["id"] == req["id"] for r in my_reqs)

    # 6. Restaurant sees the request
    rest_reqs = restaurant.get(f"/api/restaurant/donations/{d['id']}/requests").json["requests"]
    assert any(r["id"] == req["id"] for r in rest_reqs)

    # 7. Restaurant confirms delivery (transactional stock decrement)
    conf = post(restaurant, f"/api/requests/{req['id']}/confirm", {"version": req["version"]})
    assert conf.status_code == 200
    assert conf.json["request"]["status"] == "confirmed"
    updated_donation = conf.json["donation"]
    # remaining_milli decreased by 3000
    assert updated_donation["remaining_quantity"] == "7.000"
    assert updated_donation["status"] == "available"

    # 8. Beneficiary sees confirmed status with timestamp
    my_reqs2 = ben.get("/api/beneficiary/requests").json["requests"]
    confirmed = next(r for r in my_reqs2 if r["id"] == req["id"])
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_at"] is not None

    # 9. Reviewer stats reflect the cycle
    rev = make_reviewer(app)
    final_stats = rev.get("/api/reviewer/stats").json
    assert final_stats["requests"].get("confirmed", 0) >= 1
    assert final_stats["donations"].get("available", 0) >= 1


def test_exhaustion_removes_from_listing(app, restaurant):
    """When a donation is exhausted it no longer appears in the public listing."""
    profile(restaurant)
    d = publish(restaurant, quantity="2", unit="pieza").json["donation"]
    ben = make_beneficiary(app, status="approved", email="e2e-exh@demo.invalid")

    req = post(ben, f"/api/donations/{d['id']}/requests", {"quantity": "2"}).json["request"]
    conf = post(restaurant, f"/api/requests/{req['id']}/confirm", {"version": req["version"]})
    assert conf.json["donation"]["status"] == "exhausted"

    listing = ben.get("/api/donations").json["donations"]
    assert all(item["id"] != d["id"] for item in listing)

    # Direct access returns 404 for exhausted donation
    assert ben.get(f"/api/donations/{d['id']}").status_code == 404


def test_cancelled_donation_removed_from_listing(app, restaurant):
    """Cancelled donations are excluded from the beneficiary listing and return 404."""
    profile(restaurant)
    d = publish(restaurant, quantity="5", unit="pieza").json["donation"]
    ben = make_beneficiary(app, status="approved", email="e2e-cancel@demo.invalid")

    # Verify visible before cancel
    listing_before = ben.get("/api/donations").json["donations"]
    assert any(item["id"] == d["id"] for item in listing_before)

    # Restaurant cancels
    cancel_res = post(restaurant, f"/api/donations/{d['id']}/cancel", {"version": d["version"]})
    assert cancel_res.status_code == 200
    assert cancel_res.json["donation"]["status"] == "cancelled"

    # No longer visible
    listing_after = ben.get("/api/donations").json["donations"]
    assert all(item["id"] != d["id"] for item in listing_after)
    assert ben.get(f"/api/donations/{d['id']}").status_code == 404


def test_partial_requests_and_rejection(app, restaurant):
    """Multiple beneficiaries can request; excess is rejected; stock is tracked correctly."""
    profile(restaurant)
    d = publish(restaurant, quantity="5.000", unit="kg").json["donation"]

    ben1 = make_beneficiary(app, status="approved", email="e2e-b1@demo.invalid")
    ben2 = make_beneficiary(app, status="approved", email="e2e-b2@demo.invalid")

    req1 = post(ben1, f"/api/donations/{d['id']}/requests", {"quantity": "3.000"}).json["request"]
    req2 = post(ben2, f"/api/donations/{d['id']}/requests", {"quantity": "2.500"}).json["request"]

    # Confirm req1 first → 3 kg confirmed, 2 kg remaining
    conf1 = post(restaurant, f"/api/requests/{req1['id']}/confirm", {"version": req1["version"]})
    assert conf1.status_code == 200
    assert conf1.json["donation"]["remaining_quantity"] == "2.000"

    # req2 needs 2.5 kg but only 2 remain → cannot confirm
    assert post(
        restaurant, f"/api/requests/{req2['id']}/confirm", {"version": req2["version"]}
    ).status_code == 409

    # Restaurant rejects req2
    rej = post(restaurant, f"/api/requests/{req2['id']}/reject", {"version": req2["version"]})
    assert rej.status_code == 200
    assert rej.json["request"]["status"] == "rejected"


def test_beneficiary_can_cancel_pending_request(app, restaurant):
    """A beneficiary may cancel their own pending request and submit a new one."""
    profile(restaurant)
    d = publish(restaurant, quantity="5", unit="pieza").json["donation"]
    ben = make_beneficiary(app, status="approved", email="e2e-canreq@demo.invalid")

    req = post(ben, f"/api/donations/{d['id']}/requests", {"quantity": "2"}).json["request"]
    cancel_res = post(ben, f"/api/requests/{req['id']}/cancel", {"version": req["version"]})
    assert cancel_res.status_code == 200
    assert cancel_res.json["request"]["status"] == "cancelled"

    # Can now create a new request for the same donation
    req2 = post(ben, f"/api/donations/{d['id']}/requests", {"quantity": "5"})
    assert req2.status_code == 201


def test_privacy_unauthenticated_cannot_access_donations(app, restaurant):
    """Anonymous users get 401 on all protected endpoints."""
    profile(restaurant)
    d = publish(restaurant, quantity="3", unit="pieza").json["donation"]
    anon = app.test_client()

    assert anon.get("/api/donations").status_code == 401
    assert anon.get(f"/api/donations/{d['id']}").status_code == 401
    assert anon.get("/api/beneficiary/requests").status_code == 401
    assert anon.get("/api/reviewer/applications").status_code == 401
    assert anon.get("/api/reviewer/stats").status_code == 401
