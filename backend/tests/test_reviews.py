import pytest

from test_auth import app, register, post, PASSWORD
from test_applications import save, delete
from app.extensions import db
from app.models import User, ApplicationReview, Appeal


@pytest.fixture
def reviewer(app):
    with app.app_context():
        user = User(email='revisor-test@demo.invalid', role='reviewer')
        user.set_password(PASSWORD)
        db.session.add(user)
        db.session.commit()
    client = app.test_client()
    post(client, '/api/auth/login', {'email': 'revisor-test@demo.invalid', 'password': PASSWORD})
    return client


def decide(client, application, decision='approved', reason='Revisión humana de prueba: datos suficientes.'):
    token = client.get('/api/auth/csrf').json['csrf_token']
    return client.patch(f"/api/reviewer/applications/{application['id']}", json={
        'version': application['version'], 'decision': decision, 'reason': reason,
    }, headers={'X-CSRFToken': token})


def test_review_information_resubmit_and_approve(app, reviewer):
    owner = app.test_client(); register(owner)
    draft = save(owner).json['application']
    assert reviewer.get('/api/reviewer/applications').json['applications'] == []
    assert decide(reviewer, draft).status_code == 409
    sent = save(owner, version=draft['version'], action='submit').json['application']
    assert len(reviewer.get('/api/reviewer/applications').json['applications']) == 1
    clarification = decide(reviewer, sent, 'information_requested', 'Aclara el horario de recogida.').json['application']
    assert clarification['status'] == 'information_requested'
    assert owner.get('/api/applications/me').json['application']['reviews'][0]['reason'] == 'Aclara el horario de recogida.'
    assert decide(reviewer, sent).status_code == 409
    sent_again = save(owner, version=clarification['version'], action='submit').json['application']
    approved = decide(reviewer, sent_again).json['application']
    assert approved['status'] == 'approved' and len(approved['reviews']) == 2
    assert decide(reviewer, approved).status_code == 409
    assert save(owner, version=approved['version']).status_code == 409
    with app.app_context():
        reviews = db.session.scalars(db.select(ApplicationReview)).all()
        assert len(reviews) == 2 and all(review.reviewer_id for review in reviews)


def test_rejection_appeal_resolution_and_cleanup(app, reviewer):
    owner = app.test_client(); register(owner)
    sent = save(owner, action='submit').json['application']
    rejected = decide(reviewer, sent, 'rejected', 'Decisión ficticia para probar apelaciones.').json['application']
    body = {'version': rejected['version'], 'message': 'Solicito una segunda revisión de mi horario.'}
    response = post(owner, '/api/applications/me/appeals', body)
    assert response.status_code == 201
    appealed = response.json['application']
    assert appealed['status'] == 'rejected' and appealed['appeals'][0]['status'] == 'pending'
    assert post(owner, '/api/applications/me/appeals', {**body, 'version': appealed['version']}).status_code == 409
    resolved = decide(reviewer, appealed, 'information_requested', 'Indica tu horario preferido para reconsiderar.').json['application']
    assert resolved['appeals'][0]['status'] == 'resolved'
    assert resolved['appeals'][0]['resolution_review_id'] == resolved['reviews'][-1]['id']
    assert delete(owner, resolved['version']).status_code == 204
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Appeal.id))) == 0
        assert db.session.scalar(db.select(db.func.count(ApplicationReview.id))) == 0


@pytest.mark.parametrize('reason', ['', '  ', None, 'a' * 1001])
def test_reason_required(app, reviewer, reason):
    owner = app.test_client(); register(owner)
    sent = save(owner, action='submit').json['application']
    assert decide(reviewer, sent, reason=reason).status_code == 400
    assert owner.get('/api/applications/me').json['application']['status'] == 'pending'


def test_private_endpoints_and_appeal_ownership(app, reviewer):
    owner, other, restaurant = app.test_client(), app.test_client(), app.test_client()
    register(owner); register(other, email='otra@demo.invalid'); register(restaurant, email='negocio@demo.invalid', role='restaurant')
    sent = save(owner, action='submit').json['application']
    assert app.test_client().get('/api/reviewer/applications').status_code == 401
    for client in (owner, other, restaurant):
        assert client.get('/api/reviewer/applications').status_code == 403
        assert decide(client, sent).status_code == 403
    assert post(owner, '/api/applications/me/appeals', {'version': sent['version'], 'message': 'Solicitud pendiente'}).status_code == 409
    rejected = decide(reviewer, sent, 'rejected').json['application']
    assert post(other, '/api/applications/me/appeals', {'version': rejected['version'], 'message': 'Otra cuenta'}).status_code == 404
    assert post(owner, '/api/applications/me/appeals', {'version': rejected['version'], 'message': ' ', 'user_id': 2}).status_code == 400
    assert reviewer.patch(f"/api/reviewer/applications/{sent['id']}", json={}).json['error']['code'] == 'csrf'
    assert owner.post('/api/applications/me/appeals', json={}).json['error']['code'] == 'csrf'
