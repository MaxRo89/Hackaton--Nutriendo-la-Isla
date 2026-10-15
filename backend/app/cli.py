"""CLI commands for development and demo setup."""
from datetime import datetime, timedelta, timezone

import click

from .extensions import db
from .models import User, BeneficiaryApplication, RestaurantProfile, Donation


# Contraseña fija exclusivamente para la demo local con datos ficticios.
# No usar en producción ni con datos reales.
DEMO_PASSWORD = "DemoPassword123!"


def _ensure_user(role: str, authorized_restaurant: bool = False) -> "tuple[User, bool]":
    """Return (user, created) for the demo account of the given role."""
    email = f"{role}@demo.invalid"
    user = db.session.scalar(db.select(User).where(User.email == email))
    if user:
        return user, False
    user = User(email=email, role=role, restaurant_authorized=authorized_restaurant)
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user, True


def register_commands(app):
    @app.cli.command("seed-demo")
    def seed_demo():
        """Create fictional demo accounts with fixed demo password and sample data.

        Idempotent: existing accounts and their data are preserved.
        Only for local demonstration with entirely fictional data.
        """
        now = datetime.now(timezone.utc)

        # ── Restaurante ficticio preautorizado ──────────────────────────
        restaurant, rest_created = _ensure_user("restaurant", authorized_restaurant=True)
        if rest_created:
            click.echo(f"Cuenta FICTICIA creada: restaurant@demo.invalid | Contraseña: {DEMO_PASSWORD}")
        else:
            click.echo("Se conserva la cuenta existente: restaurant@demo.invalid")

        # Perfil de restaurante (solo si no existe)
        profile = db.session.get(RestaurantProfile, restaurant.id)
        if profile is None:
            profile = RestaurantProfile(
                user_id=restaurant.id,
                display_name="Restaurante Ficticio El Manglar",
                contact="Tel. ficticio: 555-0001 | manglar@demo.invalid",
                pickup_label="Frente al mercado municipal (referencia ficticia)",
                pickup_lat=18.6476,
                pickup_lng=-91.8062,
            )
            db.session.add(profile)
            db.session.flush()
            click.echo("  → Perfil de restaurante ficticio creado.")

        # Donación disponible de demo (solo si no existe ninguna del restaurante demo)
        existing_donations = db.session.scalars(
            db.select(Donation).where(
                Donation.restaurant_id == restaurant.id,
                Donation.status == "available",
            )
        ).all()
        if not existing_donations:
            pickup_snapshot = {
                "display_name": profile.display_name,
                "contact": profile.contact,
                "pickup_label": profile.pickup_label,
                "pickup_lat": profile.pickup_lat,
                "pickup_lng": profile.pickup_lng,
            }
            donation = Donation(
                restaurant_id=restaurant.id,
                title="Pan de trigo integral (ficticio)",
                description="Panes de trigo integral horneados esta mañana. Demostración local.",
                quantity_milli=20_000,  # 20 piezas
                unit="pieza",
                food_category="panaderia",
                allergens="Gluten (trigo). Puede contener trazas de lácteos.",
                storage_notes="Conservar en bolsa cerrada a temperatura ambiente, consumir antes de la fecha límite.",
                handling_notes="Envase original intacto. No requiere cadena de frío.",
                prepared_at=now - timedelta(hours=3),
                pickup_deadline=now + timedelta(hours=6),
                pickup_snapshot=pickup_snapshot,
                safety_confirmed_at=now,
                created_at=now,
            )
            db.session.add(donation)
            db.session.flush()

            # Segunda donación para dar más contexto al mapa
            donation2 = Donation(
                restaurant_id=restaurant.id,
                title="Arroz con pollo (porción ficticia)",
                description="Porciones de arroz con pollo preparadas hoy. Solo para demo.",
                quantity_milli=8_000,  # 8 porciones
                unit="porcion",
                food_category="preparada",
                allergens="Sin alérgenos declarados en esta demo.",
                storage_notes="Refrigerar a menos de 4 °C. Consumir antes del límite de recogida.",
                handling_notes="Contenedor sellado. Verificar temperatura al recoger.",
                prepared_at=now - timedelta(hours=2),
                pickup_deadline=now + timedelta(hours=4),
                pickup_snapshot=pickup_snapshot,
                safety_confirmed_at=now,
                created_at=now,
            )
            db.session.add(donation2)
            click.echo("  → Donaciones ficticias de demo creadas.")

        # ── Persona beneficiaria ficticia ──────────────────────────────
        beneficiary, ben_created = _ensure_user("beneficiary")
        if ben_created:
            click.echo(f"Cuenta FICTICIA creada: beneficiary@demo.invalid | Contraseña: {DEMO_PASSWORD}")
        else:
            click.echo("Se conserva la cuenta existente: beneficiary@demo.invalid")

        # Solicitud aprobada (solo si no existe)
        app_record = db.session.scalar(
            db.select(BeneficiaryApplication).where(
                BeneficiaryApplication.user_id == beneficiary.id
            )
        )
        if app_record is None:
            app_record = BeneficiaryApplication(
                user_id=beneficiary.id,
                answers_json={
                    "zone": "Col. Renovación (ficticio)",
                    "availability": "Lunes a viernes por las tardes",
                    "household_size": "3",
                    "dietary_restrictions": "Ninguna",
                },
                consent_at=now - timedelta(days=2),
                consent_version="v1",
                status="approved",
                submitted_at=now - timedelta(days=2),
                updated_at=now - timedelta(days=1),
            )
            db.session.add(app_record)
            click.echo("  → Solicitud de beneficiario ficticio aprobada.")

        # ── Revisor interno ────────────────────────────────────────────
        reviewer, rev_created = _ensure_user("reviewer")
        if rev_created:
            click.echo(f"Cuenta FICTICIA creada: reviewer@demo.invalid | Contraseña: {DEMO_PASSWORD}")
        else:
            click.echo("Se conserva la cuenta existente: reviewer@demo.invalid")

        db.session.commit()
        click.echo("")
        click.echo("Demo lista. Contraseña fija (solo demo): DemoPassword123!")
        click.echo("Cuentas: restaurant@demo.invalid · beneficiary@demo.invalid · reviewer@demo.invalid")
