from sqlalchemy.exc import OperationalError

from app import create_app
from app.extensions import db


def test_health_and_json_not_found():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json == {"status": "ok", "database": "ok"}
        assert client.get("/api/missing").status_code == 404
        assert client.get("/api/missing").is_json


def test_health_database_failure(monkeypatch):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})

    def unavailable(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("private database details"))

    monkeypatch.setattr(db.session, "execute", unavailable)
    response = app.test_client().get("/api/health")
    assert response.status_code == 503
    assert response.json == {"status": "unavailable", "database": "unavailable"}
    assert b"private database details" not in response.data
