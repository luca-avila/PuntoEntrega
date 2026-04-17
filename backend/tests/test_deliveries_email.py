from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

from features.deliveries.emails import (
    _build_delivery_summary_html,
    _build_delivery_summary_subject,
    _format_delivered_at_for_argentina,
)


def _build_delivery(delivered_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        location=SimpleNamespace(name="Sucursal Centro"),
        delivered_at=delivered_at,
        payment_method=SimpleNamespace(value="cash"),
        payment_notes="Pagado",
        observations="Sin novedad",
        items=[
            SimpleNamespace(
                product=SimpleNamespace(name="Harina"),
                product_id=uuid4(),
                quantity=Decimal("3.00"),
            )
        ],
    )


def test_format_delivered_at_for_argentina_from_utc_datetime():
    delivered_at = datetime(2026, 3, 18, 19, 1, tzinfo=UTC)

    formatted = _format_delivered_at_for_argentina(delivered_at)

    assert formatted == "18/03/2026 16:01 hs (Argentina, UTC-03:00)"


def test_delivery_summary_html_uses_human_readable_argentina_datetime():
    delivered_at = datetime(2026, 3, 18, 19, 1, tzinfo=UTC)
    delivery = _build_delivery(delivered_at)

    html = _build_delivery_summary_html(delivery)

    assert "18/03/2026 16:01 hs (Argentina, UTC-03:00)" in html
    assert "2026-03-18T19:01:00+00:00" not in html


def test_delivery_summary_subject_is_human_readable_and_searchable():
    delivered_at = datetime(2026, 3, 18, 19, 1, tzinfo=UTC)
    delivery_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    delivery = SimpleNamespace(
        id=delivery_id,
        location=SimpleNamespace(name="Sucursal Centro"),
        delivered_at=delivered_at,
        payment_method=SimpleNamespace(value="cash"),
        payment_notes="Pagado",
        observations="Sin novedad",
        items=[],
    )

    subject = _build_delivery_summary_subject(delivery)

    assert "PuntoEntrega" in subject
    assert "Sucursal Centro" in subject
    assert "18/03/2026 16:01 hs" in subject
    assert "Ref 123E4567" in subject
    assert str(delivery_id) not in subject


def test_delivery_summary_html_uses_short_reference_not_full_uuid():
    delivered_at = datetime(2026, 3, 18, 19, 1, tzinfo=UTC)
    delivery_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    delivery = _build_delivery(delivered_at)
    delivery.id = delivery_id

    html = _build_delivery_summary_html(delivery)

    assert "Referencia:</strong> 123E4567" in html
    assert str(delivery_id) not in html
