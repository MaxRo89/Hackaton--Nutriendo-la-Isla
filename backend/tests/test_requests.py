from datetime import datetime, timedelta, timezone
import pytest

from test_auth import app, post, register
from test_donations import restaurant, profile, publish, make_beneficiary
from app.extensions import db
from app.models import Donation, DonationRequest


def test_request_permissions_and_validation(app, restaurant):
    profile(restaurant)
    d = publish(restaurant, quantity='10', unit='pieza').json['donation']

    anon = app.test_client()
    assert post(anon, f"/api/donations/{d['id']}/requests", {'quantity': '2'}).status_code == 401

    assert post(restaurant, f"/api/donations/{d['id']}/requests", {'quantity': '2'}).status_code == 403

    unapp = make_beneficiary(app, status='pending', email='pending-ben@demo.invalid')
    assert post(unapp, f"/api/donations/{d['id']}/requests", {'quantity': '2'}).status_code == 403

    ben = make_beneficiary(app, status='approved', email='approved-ben@demo.invalid')

    # Invalid quantities
    assert post(ben, f"/api/donations/{d['id']}/requests", {'quantity': '0'}).status_code == 400
    assert post(ben, f"/api/donations/{d['id']}/requests", {'quantity': '-1'}).status_code == 400
    assert post(ben, f"/api/donations/{d['id']}/requests", {'quantity': '1.5'}).status_code == 400
    assert post(ben, f"/api/donations/{d['id']}/requests", {'quantity': 'abc'}).status_code == 400
    assert post(ben, f"/api/donations/{d['id']}/requests", {'quantity': '15'}).status_code == 400  # Exceeds 10

    # Valid request
    res = post(ben, f"/api/donations/{d['id']}/requests", {'quantity': '3', 'notes': 'Paso por la tarde'})
    assert res.status_code == 201
    req = res.json['request']
    assert req['quantity'] == '3.000'
    assert req['status'] == 'pending'
    assert req['notes'] == 'Paso por la tarde'
    assert req['donation_title'] == d['title']

    # Duplicate active request
    assert post(ben, f"/api/donations/{d['id']}/requests", {'quantity': '2'}).status_code == 409


def test_beneficiary_cancel_request(app, restaurant):
    profile(restaurant)
    d = publish(restaurant, quantity='5', unit='pieza').json['donation']
    ben = make_beneficiary(app, status='approved', email='cancelling-ben@demo.invalid')

    res = post(ben, f"/api/donations/{d['id']}/requests", {'quantity': '2'})
    req = res.json['request']

    # Cancel request
    cancel_res = post(ben, f"/api/requests/{req['id']}/cancel", {'version': req['version']})
    assert cancel_res.status_code == 200
    assert cancel_res.json['request']['status'] == 'cancelled'

    # Cannot cancel again
    assert post(ben, f"/api/requests/{req['id']}/cancel", {'version': cancel_res.json['request']['version']}).status_code == 409

    # Now beneficiary can submit a new request
    res2 = post(ben, f"/api/donations/{d['id']}/requests", {'quantity': '4'})
    assert res2.status_code == 201


def test_restaurant_confirm_and_reject(app, restaurant):
    profile(restaurant)
    d = publish(restaurant, quantity='5.000', unit='kg').json['donation']

    ben1 = make_beneficiary(app, status='approved', email='ben1@demo.invalid')
    ben2 = make_beneficiary(app, status='approved', email='ben2@demo.invalid')

    req1 = post(ben1, f"/api/donations/{d['id']}/requests", {'quantity': '3.000'}).json['request']
    req2 = post(ben2, f"/api/donations/{d['id']}/requests", {'quantity': '2.500'}).json['request']

    other_rest = app.test_client()
    register(other_rest, email='other-rest@demo.invalid', role='restaurant')
    with app.app_context():
        from app.models import User
        u = db.session.scalar(db.select(User).where(User.email == 'other-rest@demo.invalid'))
        u.restaurant_authorized = True
        db.session.commit()

    # Non-owner cannot confirm
    assert post(other_rest, f"/api/requests/{req1['id']}/confirm", {'version': req1['version']}).status_code == 404

    # Owner confirms req1 (3 kg of 5 kg confirmed)
    conf = post(restaurant, f"/api/requests/{req1['id']}/confirm", {'version': req1['version']})
    assert conf.status_code == 200
    assert conf.json['request']['status'] == 'confirmed'
    assert conf.json['donation']['remaining_quantity'] == '2.000'
    assert conf.json['donation']['status'] == 'available'

    # Trying to confirm req2 (needs 2.5 kg, but only 2 kg remaining)
    assert post(restaurant, f"/api/requests/{req2['id']}/confirm", {'version': req2['version']}).status_code == 409

    # Owner rejects req2
    rej = post(restaurant, f"/api/requests/{req2['id']}/reject", {'version': req2['version']})
    assert rej.status_code == 200
    assert rej.json['request']['status'] == 'rejected'


def test_stock_exhaustion_and_history(app, restaurant):
    profile(restaurant)
    d = publish(restaurant, quantity='2', unit='pieza').json['donation']
    ben = make_beneficiary(app, status='approved', email='ben-all@demo.invalid')

    req = post(ben, f"/api/donations/{d['id']}/requests", {'quantity': '2'}).json['request']
    conf = post(restaurant, f"/api/requests/{req['id']}/confirm", {'version': req['version']})
    assert conf.status_code == 200
    assert conf.json['donation']['status'] == 'exhausted'
    assert conf.json['donation']['remaining_quantity'] == '0.000'

    # Exhausted donation no longer appears in available donations
    available = ben.get('/api/donations').json['donations']
    assert all(item['id'] != d['id'] for item in available)

    # Beneficiary can view their own requests history
    my_reqs = ben.get('/api/beneficiary/requests').json['requests']
    assert len(my_reqs) == 1
    assert my_reqs[0]['id'] == req['id']
    assert my_reqs[0]['status'] == 'confirmed'

    # Restaurant can view requests for their donation
    rest_reqs = restaurant.get(f"/api/restaurant/donations/{d['id']}/requests").json['requests']
    assert len(rest_reqs) == 1
    assert rest_reqs[0]['id'] == req['id']
