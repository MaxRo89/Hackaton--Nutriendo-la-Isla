import pytest

from app import create_app
from app.extensions import db
from app.models import User

PASSWORD = "clave-ficticia-de-prueba"


@pytest.fixture
def app():
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


def register(client, **overrides):
    return post(client, "/api/auth/register", {
        "email": "persona@demo.invalid", "password": PASSWORD,
        "role": "beneficiary", **overrides,
    })


def test_registration_session_cookie_and_logout_revocation(app):
    client = app.test_client()
    response = register(client, email=" Persona@DEMO.invalid ")
    assert response.status_code == 201
    assert response.json["user"]["email"] == "persona@demo.invalid"
    assert "password_hash" not in response.json["user"]
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert client.get("/api/auth/me").status_code == 200
    saved_cookie = client.get_cookie("nutriendo_session").value
    with app.app_context():
        user = db.session.scalar(db.select(User))
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("scrypt:")
        assert user.check_password(PASSWORD)
    assert post(client, "/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    client.set_cookie("nutriendo_session", saved_cookie)
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("path", ["/api/auth/register", "/api/auth/login", "/api/auth/logout"])
def test_csrf_required_on_every_auth_write(app, path):
    response = app.test_client().post(path, json={})
    assert response.status_code == 400
    assert response.json["error"]["code"] == "csrf"


def test_csrf_cannot_be_reused_between_clients(app):
    first, second = app.test_client(), app.test_client()
    token = first.get("/api/auth/csrf").json["csrf_token"]
    response = second.post("/api/auth/register", json={}, headers={"X-CSRFToken": token})
    assert response.status_code == 400
    assert response.json["error"]["code"] == "csrf"


@pytest.mark.parametrize("overrides", [
    {"role": "reviewer"}, {"restaurant_authorized": True}, {"id": 1},
    {"password": "short"}, {"password": "x" * 129}, {"email": "invalid"},
    {"email": None}, {"role": ["reviewer"]},
])
def test_invalid_or_privileged_registration_rejected(app, overrides):
    assert register(app.test_client(), **overrides).status_code == 400
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(User.id))) == 0


def test_duplicate_email_and_wrong_password(app):
    first = app.test_client()
    assert register(first).status_code == 201
    second = app.test_client()
    assert register(second, email="PERSONA@DEMO.INVALID").status_code == 409
    for email in ("persona@demo.invalid", "missing@demo.invalid"):
        response = post(second, "/api/auth/login", {"email": email, "password": "incorrecta-pero-larga"})
        assert response.status_code == 401
        assert response.json["error"]["message"] == "Correo o contraseña incorrectos."
    assert post(second, "/api/auth/login", {"email": "persona@demo.invalid", "password": PASSWORD}).status_code == 200
    # A new login invalidates the older session rather than trusting a stale cookie.
    assert first.get("/api/auth/me").status_code == 401


def test_role_boundaries_and_database_authorization(app):
    guest = app.test_client()
    for role in ("restaurant", "beneficiary", "reviewer"):
        assert guest.get(f"/api/{role}/access").status_code == 401
    client = app.test_client()
    register(client)
    assert client.get("/api/beneficiary/access").status_code == 200
    assert client.get("/api/restaurant/access").status_code == 403
    assert client.get("/api/reviewer/access").status_code == 403
    restaurant = app.test_client()
    register(restaurant, email="restaurante@demo.invalid", role="restaurant")
    assert restaurant.get("/api/restaurant/access").status_code == 403
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.role == "restaurant"))
        user.restaurant_authorized = True
        db.session.commit()
    assert restaurant.get("/api/restaurant/access").status_code == 200
    assert restaurant.get("/api/beneficiary/access").status_code == 403
    assert restaurant.get("/api/reviewer/access").status_code == 403
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.role == "restaurant"))
        user.restaurant_authorized = False
        db.session.commit()
    assert restaurant.get("/api/restaurant/access").status_code == 403


def test_seed_demo_is_idempotent_and_reviewer_login(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-demo"])
    assert result.exit_code == 0
    reviewer_line = next(line for line in result.output.splitlines() if "reviewer@" in line)
    # The new cli.py uses the fixed DEMO_PASSWORD for all demo accounts.
    password = reviewer_line.split("Contraseña: ")[1]
    with app.app_context():
        before = [(u.email, u.password_hash) for u in db.session.scalars(db.select(User).order_by(User.id))]
        # seed-demo creates restaurant, beneficiary and reviewer accounts
        assert len(before) >= 3
    second = runner.invoke(args=["seed-demo"])
    assert second.exit_code == 0
    assert "Se conserva" in second.output  # idempotent: preserves existing accounts
    with app.app_context():
        after = [(u.email, u.password_hash) for u in db.session.scalars(db.select(User).order_by(User.id))]
        assert before[:3] == after[:3]  # first three accounts unchanged
    client = app.test_client()
    assert post(client, "/api/auth/login", {"email": "reviewer@demo.invalid", "password": password}).status_code == 200
    assert client.get("/api/reviewer/access").status_code == 200
    assert client.get("/api/restaurant/access").status_code == 403


def test_secure_cookie_configuration(app):
    app.config["SESSION_COOKIE_SECURE"] = True
    response = app.test_client().get("/api/auth/csrf")
    assert "Secure;" in response.headers["Set-Cookie"]
    assert response.headers["Cache-Control"] == "no-store"
