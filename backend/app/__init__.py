from pathlib import Path
import os
import secrets

from dotenv import load_dotenv
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from flask_wtf.csrf import CSRFError

from .config import configuration
from .extensions import db, migrate, login_manager, csrf
from .routes.health import health
from .routes.auth import auth
from .routes.applications import applications
from .routes.reviewer import reviewer
from .routes.donations import donations
from .routes.requests import requests_bp
from .routes.ai import ai
from .cli import register_commands


def create_app(test_config=None):
    if not test_config:
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(configuration())
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config["SECRET_KEY"]:
        # Local-only persistent random secret, excluded from version control.
        secret_path = Path(app.instance_path) / "session-secret"
        try:
            descriptor = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "w") as secret_file:
                secret_file.write(secrets.token_hex(32))
        app.config["SECRET_KEY"] = secret_path.read_text().strip()
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(health, url_prefix="/api")
    app.register_blueprint(auth, url_prefix="/api")
    app.register_blueprint(applications, url_prefix="/api")
    app.register_blueprint(reviewer, url_prefix="/api")
    app.register_blueprint(donations, url_prefix="/api")
    app.register_blueprint(requests_bp, url_prefix="/api")
    app.register_blueprint(ai, url_prefix="/api")
    register_commands(app)

    @app.after_request
    def private_response(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return jsonify(error={"code": "csrf", "message": "La sesión del formulario venció. Inténtalo de nuevo."}), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error={"code": error.code, "message": error.description}), error.code

    return app
