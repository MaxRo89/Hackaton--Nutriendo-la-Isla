from flask import Blueprint, abort, jsonify, request

from ..ai_client import generate_application_summary, generate_donation_hints
from ..auth import role_required

ai = Blueprint("ai", __name__)


@ai.post("/ai/donation-hints")
@role_required("restaurant", authorized_restaurant=True)
def donation_hints():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Envía un objeto JSON válido.")
    allowed = {"title", "description", "allergens", "storage_notes", "handling_notes", "food_category"}
    if set(data) - allowed:
        abort(400, description="La petición contiene campos no permitidos.")
    payload = {key: (data.get(key) or "") for key in allowed}
    return jsonify(hints=generate_donation_hints(payload))


@ai.post("/ai/application-summary")
@role_required("reviewer")
def application_summary():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Envía un objeto JSON válido.")
    answers = data.get("answers")
    if not isinstance(answers, dict):
        abort(400, description="La petición debe incluir un objeto answers.")
    return jsonify(summary=generate_application_summary(answers))
