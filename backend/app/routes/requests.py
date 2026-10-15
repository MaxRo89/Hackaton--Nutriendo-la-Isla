from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user

from ..auth import role_required
from ..extensions import db
from ..models import Donation, DonationRequest
from .applications import commit
from .donations import body, check_version

requests_bp = Blueprint('requests', __name__)


def parse_quantity(raw, unit):
    if not isinstance(raw, str) or len(raw) > 20:
        abort(400, description='Indica una cantidad válida.')
    try:
        qty = Decimal(raw)
        if not qty.is_finite() or not 0 < qty <= 100000:
            raise ValueError()
        scaled = qty * 1000
        if scaled != scaled.to_integral_value() or (unit != 'kg' and qty != qty.to_integral_value()):
            raise ValueError()
        return int(scaled)
    except (InvalidOperation, ValueError):
        abort(400, description='Usa cantidades positivas: piezas/porciones enteras o kg con hasta 3 decimales.')


@requests_bp.post('/donations/<int:donation_id>/requests')
@role_required('beneficiary', approved_beneficiary=True)
def create_request(donation_id):
    data = body(('quantity', 'notes'))
    donation = db.session.get(Donation, donation_id)
    now = datetime.now(timezone.utc)
    if donation is None or donation.status != 'available' or donation.pickup_deadline.replace(tzinfo=timezone.utc) <= now:
        abort(404, description='Donación no encontrada o no disponible.')

    requested_milli = parse_quantity(data.get('quantity'), donation.unit)
    if requested_milli > donation.remaining_milli:
        rem_str = f"{donation.remaining_milli // 1000}.{donation.remaining_milli % 1000:03d}"
        abort(400, description=f'La cantidad solicitada supera las existencias disponibles ({rem_str} {donation.unit}).')

    existing = db.session.scalar(
        db.select(DonationRequest).where(
            DonationRequest.donation_id == donation_id,
            DonationRequest.beneficiary_id == current_user.id,
            DonationRequest.status.in_(('pending', 'confirmed')),
        )
    )
    if existing:
        abort(409, description='Ya tienes una solicitud activa para este alimento.')

    notes = data.get('notes')
    if notes is not None:
        if not isinstance(notes, str) or len(notes) > 500:
            abort(400, description='Las notas opcionales no deben superar 500 caracteres.')
        notes = notes.strip()

    req = DonationRequest(
        donation_id=donation.id,
        beneficiary_id=current_user.id,
        quantity_milli=requested_milli,
        status='pending',
        notes=notes,
        requested_at=now,
    )
    db.session.add(req)
    commit()
    return jsonify(request=req.public_data()), 201


@requests_bp.get('/beneficiary/requests')
@role_required('beneficiary', approved_beneficiary=True)
def my_requests():
    items = db.session.scalars(
        db.select(DonationRequest)
        .where(DonationRequest.beneficiary_id == current_user.id)
        .order_by(DonationRequest.id.desc())
    ).all()
    return jsonify(requests=[item.public_data() for item in items])


@requests_bp.post('/requests/<int:request_id>/cancel')
@role_required('beneficiary')
def cancel_request(request_id):
    data = body(('version',))
    req = db.session.scalar(
        db.select(DonationRequest).where(
            DonationRequest.id == request_id,
            DonationRequest.beneficiary_id == current_user.id,
        )
    )
    if req is None:
        abort(404, description='Solicitud no encontrada.')
    check_version(data, req)
    if req.status != 'pending':
        abort(409, description='Solo puedes cancelar una solicitud en estado pendiente.')

    req.status = 'cancelled'
    req.cancelled_at = datetime.now(timezone.utc)
    commit()
    return jsonify(request=req.public_data())


@requests_bp.get('/restaurant/donations/<int:donation_id>/requests')
@role_required('restaurant', authorized_restaurant=True)
def donation_requests(donation_id):
    donation = db.session.scalar(
        db.select(Donation).where(
            Donation.id == donation_id,
            Donation.restaurant_id == current_user.id,
        )
    )
    if donation is None:
        abort(404, description='Donación no encontrada.')
    items = db.session.scalars(
        db.select(DonationRequest)
        .where(DonationRequest.donation_id == donation_id)
        .order_by(DonationRequest.id.desc())
    ).all()
    return jsonify(requests=[item.public_data() for item in items])


@requests_bp.post('/requests/<int:request_id>/confirm')
@role_required('restaurant', authorized_restaurant=True)
def confirm_delivery(request_id):
    data = body(('version',))
    req = db.session.get(DonationRequest, request_id)
    if req is None or req.donation.restaurant_id != current_user.id:
        abort(404, description='Solicitud no encontrada.')
    check_version(data, req)
    if req.status != 'pending':
        abort(409, description='Solo puedes confirmar una solicitud en estado pendiente.')

    now = datetime.now(timezone.utc)
    donation = req.donation
    if donation.status != 'available' or donation.pickup_deadline.replace(tzinfo=timezone.utc) <= now:
        abort(409, description='La donación ya no está disponible o ha vencido.')

    if donation.remaining_milli < req.quantity_milli:
        abort(409, description='Las existencias disponibles son insuficientes para confirmar esta entrega.')

    req.status = 'confirmed'
    req.confirmed_at = now
    commit()
    return jsonify(request=req.public_data(), donation=donation.public_data())


@requests_bp.post('/requests/<int:request_id>/reject')
@role_required('restaurant', authorized_restaurant=True)
def reject_request(request_id):
    data = body(('version',))
    req = db.session.get(DonationRequest, request_id)
    if req is None or req.donation.restaurant_id != current_user.id:
        abort(404, description='Solicitud no encontrada.')
    check_version(data, req)
    if req.status != 'pending':
        abort(409, description='Solo puedes rechazar una solicitud en estado pendiente.')

    req.status = 'rejected'
    commit()
    return jsonify(request=req.public_data())
