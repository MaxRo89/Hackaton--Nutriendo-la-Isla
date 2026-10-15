import pytest

from test_auth import app, register, post
from app.extensions import db
from app.models import BeneficiaryApplication


def save(client, version=0, action="save", **changes):
    body = {"version": version, "action": action, "consent": True,
            "consent_version": "demo-local-v1", "answers": {"zone": "Zona ficticia", "availability": "Tardes"}, **changes}
    return post(client, "/api/applications/me", body)


def delete(client, version):
    token = client.get('/api/auth/csrf').json['csrf_token']
    return client.delete('/api/applications/me', json={"version": version}, headers={"X-CSRFToken": token})


def test_draft_submit_edit_and_delete(app):
    client = app.test_client()
    register(client)
    assert client.get('/api/applications/me').json['application'] is None
    draft = save(client, answers={}).json['application']
    assert draft['status'] == 'draft' and draft['submitted_at'] is None
    assert draft['consent_at'] and draft['consent_version'] == 'demo-local-v1'
    pending = save(client, version=draft['version'], action='submit').json['application']
    assert pending['status'] == 'pending' and pending['submitted_at']
    assert pending['consent_at'] == draft['consent_at']
    assert client.get('/api/applications/me').json['application'] == pending
    revised = save(client, version=pending['version']).json['application']
    assert revised['status'] == 'draft' and revised['submitted_at'] is None
    assert delete(client, revised['version']).status_code == 204
    assert client.get('/api/applications/me').json['application'] is None
    assert client.get('/api/auth/me').status_code == 200


@pytest.mark.parametrize('changes', [
    {'consent': False}, {'consent': 'true'}, {'consent_version': 'old'},
    {'answers': {'zone': 'x' * 121}}, {'answers': {'household_size': True}},
    {'answers': {'household_size': 1.5}}, {'answers': {'household_size': 0}},
    {'answers': {'refrigeration': ['yes']}}, {'answers': {'private_address': 'hidden'}},
    {'status': 'approved'}, {'user_id': 2}, {'action': 'approve'}, {'version': True},
])
def test_validation_does_not_persist_invalid_answers(app, changes):
    client = app.test_client()
    register(client)
    assert save(client, **changes).status_code == 400
    assert client.get('/api/applications/me').json['application'] is None


def test_submit_requires_only_logistics_and_consent(app):
    client = app.test_client()
    register(client)
    assert save(client, action='submit', answers={'zone': '  '}).status_code == 400
    result = save(client, action='submit')
    assert result.status_code == 200
    assert result.json['application']['answers']['economic_context'] == ''


def test_roles_ownership_and_csrf(app):
    guest = app.test_client()
    assert guest.get('/api/applications/me').status_code == 401
    owner, other, restaurant = app.test_client(), app.test_client(), app.test_client()
    register(owner)
    register(other, email='otra@demo.invalid')
    register(restaurant, email='negocio@demo.invalid', role='restaurant')
    saved = save(owner).json['application']
    assert other.get('/api/applications/me').json['application'] is None
    assert save(other, user_id=1).status_code == 400
    assert delete(other, 0).status_code == 204
    assert owner.get('/api/applications/me').json['application']['id'] == saved['id']
    assert restaurant.get('/api/applications/me').status_code == 403
    assert save(restaurant).status_code == 403
    assert owner.post('/api/applications/me', json={}).json['error']['code'] == 'csrf'
    assert owner.delete('/api/applications/me', json={}).json['error']['code'] == 'csrf'
    assert owner.get('/api/applications/' + str(saved['id'])).status_code == 404


def test_stale_edits_and_reviewed_states_cannot_be_overwritten(app):
    client = app.test_client()
    register(client)
    application = save(client).json['application']
    assert save(client, version=0).status_code == 409
    assert delete(client, 0).status_code == 409
    with app.app_context():
        stored = db.session.get(BeneficiaryApplication, application['id'])
        stored.status = 'approved'
        db.session.commit()
        version = stored.version
    assert save(client, version=version).status_code == 409
    assert delete(client, version).status_code == 409
