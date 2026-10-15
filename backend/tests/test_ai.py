import os

import pytest

from app import create_app
from app.extensions import db
from app.models import User

PASSWORD = "clave-ficticia-de-prueba"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "only-for-isolated-tests",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def post(client, path, body=None):
    token = client.get("/api/auth/csrf").json["csrf_token"]
    return client.post(path, json=body, headers={"X-CSRFToken": token})


def register(client, email, role):
    return post(client, "/api/auth/register", {
        "email": email,
        "password": PASSWORD,
        "role": role,
    })


def login(client, email):
    return post(client, "/api/auth/login", {
        "email": email,
        "password": PASSWORD,
    })


def test_hints_requires_authorized_restaurant(app):
    guest = app.test_client()
    token = guest.get("/api/auth/csrf").json["csrf_token"]
    assert guest.post("/api/ai/donation-hints", json={
        "title": "Pan",
        "description": "Pan de ayer",
        "allergens": "Sin alergias",
        "storage_notes": "Guardar en caja",
        "handling_notes": "Usar guantes",
        "food_category": "panaderia",
    }, headers={"X-CSRFToken": token}).status_code == 401

    beneficiary = app.test_client()
    register(beneficiary, "beneficiary@demo.invalid", "beneficiary")
    token = beneficiary.get("/api/auth/csrf").json["csrf_token"]
    assert beneficiary.post("/api/ai/donation-hints", json={
        "title": "Pan",
        "description": "Pan de ayer",
        "allergens": "Sin alergias",
        "storage_notes": "Guardar en caja",
        "handling_notes": "Usar guantes",
        "food_category": "panaderia",
    }, headers={"X-CSRFToken": token}).status_code == 403

    restaurant = app.test_client()
    register(restaurant, "restaurant@demo.invalid", "restaurant")
    token = restaurant.get("/api/auth/csrf").json["csrf_token"]
    assert restaurant.post("/api/ai/donation-hints", json={
        "title": "Pan",
        "description": "Pan de ayer",
        "allergens": "Sin alergias",
        "storage_notes": "Guardar en caja",
        "handling_notes": "Usar guantes",
        "food_category": "panaderia",
    }, headers={"X-CSRFToken": token}).status_code == 403


def test_hints_returns_list_without_api_key(app):
    restaurant = app.test_client()
    register(restaurant, "restaurant@demo.invalid", "restaurant")
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == "restaurant@demo.invalid"))
        user.restaurant_authorized = True
        db.session.commit()
    token = restaurant.get("/api/auth/csrf").json["csrf_token"]
    response = restaurant.post("/api/ai/donation-hints", json={
        "title": "Pan",
        "description": "Pan de ayer",
        "allergens": "Sin alergias",
        "storage_notes": "Guardar en caja",
        "handling_notes": "Usar guantes",
        "food_category": "panaderia",
    }, headers={"X-CSRFToken": token})
    assert response.status_code == 200
    assert response.json == {"hints": []}


def test_summary_requires_reviewer(app):
    guest = app.test_client()
    token = guest.get("/api/auth/csrf").json["csrf_token"]
    assert guest.post("/api/ai/application-summary", json={"answers": {}}, headers={"X-CSRFToken": token}).status_code == 401

    restaurant = app.test_client()
    register(restaurant, "restaurant@demo.invalid", "restaurant")
    token = restaurant.get("/api/auth/csrf").json["csrf_token"]
    assert restaurant.post("/api/ai/application-summary", json={"answers": {}}, headers={"X-CSRFToken": token}).status_code == 403

    beneficiary = app.test_client()
    register(beneficiary, "beneficiary@demo.invalid", "beneficiary")
    token = beneficiary.get("/api/auth/csrf").json["csrf_token"]
    assert beneficiary.post("/api/ai/application-summary", json={"answers": {}}, headers={"X-CSRFToken": token}).status_code == 403


def test_summary_returns_empty_without_api_key(app):
    reviewer = app.test_client()
    register(reviewer, "reviewer@demo.invalid", "beneficiary")
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == "reviewer@demo.invalid"))
        user.role = "reviewer"
        db.session.commit()
    token = reviewer.get("/api/auth/csrf").json["csrf_token"]
    response = reviewer.post("/api/ai/application-summary", json={"answers": {"zone": "Centro", "availability": "Lunes y miercoles", "household_size": 3}}, headers={"X-CSRFToken": token})
    assert response.status_code == 200
    assert response.json == {"summary": ""}
