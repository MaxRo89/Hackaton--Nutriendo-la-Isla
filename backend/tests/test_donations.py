from datetime import datetime, timedelta, timezone
import pytest

from test_auth import app, post, register
from app.extensions import db
from app.models import User, Donation, BeneficiaryApplication


def profile(client, **changes):
    token = client.get('/api/auth/csrf').json['csrf_token']
    return client.put('/api/restaurant/profile', json={
        'display_name': 'Restaurante ficticio', 'contact': 'contacto@demo.invalid',
        'pickup_label': 'Punto simulado', 'pickup_lat': 18.65, 'pickup_lng': -91.8, 'version': 0, **changes,
    }, headers={'X-CSRFToken': token})


@pytest.fixture
def restaurant(app):
    client = app.test_client()
    register(client, email='restaurante@demo.invalid', role='restaurant')
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == 'restaurante@demo.invalid'))
        user.restaurant_authorized = True
        db.session.commit()
    return client


def publish(client, **changes):
    return post(client, '/api/donations', {
        'title': 'Pan ficticio', 'description': 'Lote simulado', 'quantity': '15', 'unit': 'pieza',
        'food_category': 'panaderia', 'allergens': 'Trigo (dato ficticio)',
        'storage_notes': 'Conservación ficticia documentada', 'handling_notes': 'Envase simulado revisado',
        'prepared_at': None, 'pickup_deadline': (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        'safety_confirmed': True, **changes,
    })


def test_profile_publish_snapshot_and_cancel(app, restaurant):
    assert publish(restaurant).status_code == 409
    saved = profile(restaurant).json['profile']
    assert restaurant.get('/api/restaurant/profile').json['profile'] == saved
    response = publish(restaurant, quantity='2.125', unit='kg')
    assert response.status_code == 201
    donation = response.json['donation']
    assert donation['quantity'] == '2.125' and donation['status'] == 'available'
    assert profile(restaurant, version=saved['version'], pickup_label='Nuevo punto').status_code == 200
    listed = restaurant.get('/api/restaurant/donations').json['donations']
    assert listed[0]['pickup']['pickup_label'] == 'Punto simulado'
    assert profile(restaurant, version=saved['version']).status_code == 409
    with app.app_context():
        assert db.session.get(Donation, donation['id']).quantity_milli == 2125
    path = f"/api/donations/{donation['id']}/cancel"
    assert post(restaurant, path, {'version': 0}).status_code == 409
    cancelled = post(restaurant, path, {'version': donation['version']})
    assert cancelled.json['donation']['status'] == 'cancelled'
    assert len(restaurant.get('/api/restaurant/donations').json['donations']) == 1


@pytest.mark.parametrize('changes', [
    {'quantity': '0'}, {'quantity': '-1'}, {'quantity': '1.5'}, {'quantity': 'NaN'},
    {'quantity': 'Infinity'}, {'quantity': '100001'}, {'quantity': 3},
    {'quantity': '0.0001', 'unit': 'kg'}, {'unit': 'litros'}, {'food_category': 'otro'},
    {'allergens': ' '}, {'storage_notes': ''}, {'handling_notes': ''},
    {'safety_confirmed': False}, {'safety_confirmed': 'true'},
    {'food_category': 'preparada', 'prepared_at': None}, {'prepared_at': 'invalid'},
    {'pickup_deadline': '2000-01-01T12:00:00+00:00'}, {'pickup_deadline': '2099-01-01T12:00'},
    {'prepared_at': '2099-01-01T12:00:00+00:00'}, {'restaurant_id': 99}, {'status': 'available'},
])
def test_invalid_publication_not_persisted(app, restaurant, changes):
    profile(restaurant)
    assert publish(restaurant, **changes).status_code == 400
    assert restaurant.get('/api/restaurant/donations').json['donations'] == []


def test_permissions_ownership_and_csrf(app, restaurant):
    profile(restaurant)
    donation = publish(restaurant).json['donation']
    beneficiary, other = app.test_client(), app.test_client()
    register(beneficiary)
    register(other, email='otro@demo.invalid', role='restaurant')
    assert beneficiary.get('/api/restaurant/profile').status_code == 403
    assert publish(beneficiary).status_code == 403
    assert profile(other).status_code == 200
    assert publish(other).status_code == 403
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == 'otro@demo.invalid'))
        user.restaurant_authorized = True
        db.session.commit()
    assert other.get('/api/restaurant/donations').json['donations'] == []
    assert post(other, f"/api/donations/{donation['id']}/cancel", {'version': donation['version']}).status_code == 404
    assert restaurant.post('/api/donations', json={}).json['error']['code'] == 'csrf'
    assert restaurant.put('/api/restaurant/profile', json={}).json['error']['code'] == 'csrf'
    assert app.test_client().get('/api/restaurant/profile').status_code == 401


@pytest.mark.parametrize('changes', [{'pickup_lat': 91}, {'pickup_lng': -181}, {'pickup_lat': True}, {'pickup_lat': None}, {'display_name': ''}, {'contact': 'x' * 201}])
def test_invalid_profile(app, restaurant, changes):
    assert profile(restaurant, **changes).status_code == 400
    assert restaurant.get('/api/restaurant/profile').json['profile'] is None


def test_expired_status_is_enforced_by_server(app, restaurant):
    profile(restaurant)
    donation = publish(restaurant, food_category='preparada', prepared_at=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()).json['donation']
    with app.app_context():
        stored = db.session.get(Donation, donation['id'])
        stored.pickup_deadline = datetime.now(timezone.utc)-timedelta(minutes=1)
        db.session.commit()
    expired = restaurant.get('/api/restaurant/donations').json['donations'][0]
    assert expired['status'] == 'expired'
    assert post(restaurant, f"/api/donations/{expired['id']}/cancel", {'version': expired['version']}).status_code == 409


def make_beneficiary(app, status='approved', email=None):
    client = app.test_client()
    ben_email = email or f"ben-{status or 'none'}@demo.invalid"
    register(client, email=ben_email, role='beneficiary')
    if status is not None:
        with app.app_context():
            user = db.session.scalar(db.select(User).where(User.email == ben_email))
            now = datetime.now(timezone.utc)
            record = BeneficiaryApplication(
                user_id=user.id,
                answers_json={'zone': 'Centro', 'availability': 'Tardes'},
                consent_at=now,
                consent_version='demo-local-v1',
                status=status,
                submitted_at=now,
                updated_at=now,
            )
            db.session.add(record)
            db.session.commit()
    return client


def test_discovery_permissions_and_approval_required(app, restaurant):
    profile(restaurant)
    d = publish(restaurant).json['donation']
    anon = app.test_client()
    assert anon.get('/api/donations').status_code == 401
    assert anon.get(f"/api/donations/{d['id']}").status_code == 401

    assert restaurant.get('/api/donations').status_code == 403
    assert restaurant.get(f"/api/donations/{d['id']}").status_code == 403

    reviewer = app.test_client()
    with app.app_context():
        rev_user = User(email='revisor-p6@demo.invalid', role='reviewer')
        rev_user.set_password('revisor12345678')
        db.session.add(rev_user)
        db.session.commit()
    post(reviewer, '/api/auth/login', {'email': 'revisor-p6@demo.invalid', 'password': 'revisor12345678'})
    assert reviewer.get('/api/donations').status_code == 403
    assert reviewer.get(f"/api/donations/{d['id']}").status_code == 403

    unapplied = make_beneficiary(app, status=None)
    assert unapplied.get('/api/donations').status_code == 403
    assert unapplied.get(f"/api/donations/{d['id']}").status_code == 403

    for unapproved_status in ('draft', 'pending', 'information_requested', 'rejected'):
        client = make_beneficiary(app, status=unapproved_status)
        assert client.get('/api/donations').status_code == 403
        assert client.get(f"/api/donations/{d['id']}").status_code == 403

    approved = make_beneficiary(app, status='approved')
    assert approved.get('/api/donations').status_code == 200
    assert approved.get(f"/api/donations/{d['id']}").status_code == 200


def test_discovery_exclusions_snapshot_and_detail(app, restaurant):
    prof_resp = profile(restaurant, pickup_lat=18.651, pickup_lng=-91.802, pickup_label='Punto original').json['profile']
    d1 = publish(restaurant, title='Donación disponible').json['donation']
    d2 = publish(restaurant, title='Donación a cancelar').json['donation']
    d3 = publish(restaurant, title='Donación a vencer').json['donation']

    approved = make_beneficiary(app, status='approved')

    initial_list = approved.get('/api/donations').json['donations']
    assert len(initial_list) == 3

    # Cancel d2
    post(restaurant, f"/api/donations/{d2['id']}/cancel", {'version': d2['version']})

    # Expire d3
    with app.app_context():
        stored3 = db.session.get(Donation, d3['id'])
        stored3.pickup_deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.session.commit()

    # Update restaurant profile with new location
    profile(restaurant, version=prof_resp['version'], pickup_lat=19.000, pickup_lng=-90.000, pickup_label='Nuevo punto')

    # Query list as approved beneficiary
    available = approved.get('/api/donations').json['donations']
    assert len(available) == 1
    item = available[0]
    assert item['id'] == d1['id']
    assert item['title'] == 'Donación disponible'
    assert item['status'] == 'available'
    # Check that snapshot was preserved, not overwritten by updated profile
    assert item['pickup']['pickup_lat'] == 18.651
    assert item['pickup']['pickup_lng'] == -91.802
    assert item['pickup']['pickup_label'] == 'Punto original'

    # Direct detail access
    detail1 = approved.get(f"/api/donations/{d1['id']}")
    assert detail1.status_code == 200
    assert detail1.json['donation']['id'] == d1['id']
    assert detail1.json['donation']['pickup']['pickup_label'] == 'Punto original'

    # Cancelled and expired direct detail access must be 404
    assert approved.get(f"/api/donations/{d2['id']}").status_code == 404
    assert approved.get(f"/api/donations/{d3['id']}").status_code == 404
    assert approved.get('/api/donations/99999').status_code == 404
