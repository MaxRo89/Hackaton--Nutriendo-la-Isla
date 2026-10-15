from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user

from ..auth import role_required
from ..extensions import db
from ..models import RestaurantProfile, Donation
from .applications import commit

donations = Blueprint('donations', __name__)


def body(allowed):
    data = request.get_json()
    if not isinstance(data, dict) or set(data) - set(allowed):
        abort(400, description='La petición contiene campos no permitidos.')
    return data


def text_field(data, key, limit):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        abort(400, description=f'Completa {key} con un máximo de {limit} caracteres.')
    return value.strip()


def check_version(data, item):
    if type(data.get('version')) is not int or data['version'] != (item.version if item else 0):
        abort(409, description='Los datos cambiaron. Actualiza antes de continuar.')


def timestamp(value, optional=False):
    if optional and value in (None, ''):
        return None
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.utcoffset() is None:
            raise ValueError()
        return date.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError, OverflowError):
        abort(400, description='Envía fechas válidas con zona horaria.')


@donations.get('/restaurant/profile')
@role_required('restaurant')
def get_profile():
    profile = db.session.get(RestaurantProfile, current_user.id)
    return jsonify(profile=profile.public_data() if profile else None)


@donations.put('/restaurant/profile')
@role_required('restaurant')
def save_profile():
    data = body(('display_name', 'contact', 'pickup_label', 'pickup_lat', 'pickup_lng', 'version'))
    profile = db.session.get(RestaurantProfile, current_user.id)
    check_version(data, profile)
    values = {key: text_field(data, key, limit) for key, limit in [('display_name', 120), ('contact', 200), ('pickup_label', 200)]}
    for key, low, high in [('pickup_lat', -90, 90), ('pickup_lng', -180, 180)]:
        value = data.get(key)
        if type(value) not in (float, int) or not low <= value <= high or not math.isfinite(value):
            abort(400, description='Indica coordenadas válidas para el punto de recogida.')
        values[key] = value
    if profile is None:
        profile = RestaurantProfile(user_id=current_user.id)
        db.session.add(profile)
    for key, value in values.items():
        setattr(profile, key, value)
    commit()
    return jsonify(profile=profile.public_data())


@donations.get('/restaurant/donations')
@role_required('restaurant', authorized_restaurant=True)
def own_donations():
    items = db.session.scalars(db.select(Donation).where(Donation.restaurant_id == current_user.id).order_by(Donation.id.desc())).all()
    return jsonify(donations=[item.public_data() for item in items])


@donations.post('/donations')
@role_required('restaurant', authorized_restaurant=True)
def publish():
    data = body(('title', 'description', 'quantity', 'unit', 'food_category', 'allergens', 'storage_notes', 'handling_notes', 'prepared_at', 'pickup_deadline', 'safety_confirmed'))
    profile = db.session.get(RestaurantProfile, current_user.id)
    if profile is None:
        abort(409, description='Completa primero el perfil y el punto de recogida.')
    values = {key: text_field(data, key, limit) for key, limit in [('title', 120), ('description', 1000), ('allergens', 500), ('storage_notes', 500), ('handling_notes', 500)]}
    if data.get('unit') not in ('pieza', 'porcion', 'kg') or data.get('food_category') not in ('panaderia', 'envasado', 'preparada', 'fresco'):
        abort(400, description='Selecciona unidad y categoría válidas.')
    try:
        raw = data.get('quantity')
        if not isinstance(raw, str) or len(raw) > 20:
            raise ValueError()
        quantity = Decimal(raw)
        if not quantity.is_finite() or not 0 < quantity <= 100000:
            raise ValueError()
        scaled = quantity * 1000
        if scaled != scaled.to_integral_value() or (data['unit'] != 'kg' and quantity != quantity.to_integral_value()):
            raise ValueError()
    except (InvalidOperation, ValueError):
        abort(400, description='Usa cantidades positivas: piezas/porciones enteras o kg con hasta 3 decimales (máximo 100000).')
    now = datetime.now(timezone.utc)
    deadline = timestamp(data.get('pickup_deadline'))
    prepared = timestamp(data.get('prepared_at'), optional=True)
    if deadline <= now or (prepared and (prepared > now or prepared >= deadline)):
        abort(400, description='La recogida debe ser futura y la preparación no puede ser futura ni posterior a la recogida.')
    if data['food_category'] == 'preparada' and prepared is None:
        abort(400, description='La comida preparada requiere fecha y hora de preparación.')
    if data.get('safety_confirmed') is not True:
        abort(400, description='Confirma la revisión responsable de los datos de esta donación ficticia.')
    pickup = profile.public_data()
    pickup.pop('version')
    donation = Donation(**values, restaurant_id=current_user.id, quantity_milli=int(scaled),
        unit=data['unit'], food_category=data['food_category'], prepared_at=prepared,
        pickup_deadline=deadline, pickup_snapshot=pickup, safety_confirmed_at=now, created_at=now)
    db.session.add(donation)
    commit()
    return jsonify(donation=donation.public_data()), 201


@donations.post('/donations/<int:donation_id>/cancel')
@role_required('restaurant', authorized_restaurant=True)
def cancel(donation_id):
    data = body(('version',))
    donation = db.session.scalar(db.select(Donation).where(Donation.id == donation_id, Donation.restaurant_id == current_user.id))
    if donation is None:
        abort(404, description='Donación no encontrada.')
    check_version(data, donation)
    if donation.public_data()['status'] != 'available':
        abort(409, description='Solo puedes cancelar una donación vigente y disponible.')
    donation.status = 'cancelled'
    commit()
    return jsonify(donation=donation.public_data())


@donations.get('/donations')
@role_required('beneficiary', approved_beneficiary=True)
def list_available():
    now = datetime.now(timezone.utc)
    items = db.session.scalars(
        db.select(Donation)
        .where(Donation.status == 'available', Donation.pickup_deadline > now)
        .order_by(Donation.pickup_deadline.asc())
    ).all()
    available = [item.public_data() for item in items if item.public_data()['status'] == 'available']
    return jsonify(donations=available)


@donations.get('/donations/<int:donation_id>')
@role_required('beneficiary', approved_beneficiary=True)
def get_available(donation_id):
    donation = db.session.get(Donation, donation_id)
    if donation is None:
        abort(404, description='Donación no encontrada.')
    data = donation.public_data()
    if data['status'] != 'available':
        abort(404, description='Donación no encontrada o no disponible.')
    return jsonify(donation=data)
