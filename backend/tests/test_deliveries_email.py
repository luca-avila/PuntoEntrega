from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from features.deliveries.email import (
    _build_delivery_summary_html,
    _format_delivered_at_for_argentina,
    _resolve_recipients,
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


def test_resolve_recipients_uses_override_when_provided():
    recipients = _resolve_recipients(
        default_recipients_raw="equipo@example.com,ops@example.com",
        summary_recipient_email="  custom@example.com  ",
    )

    assert recipients == ["custom@example.com"]


def test_resolve_recipients_falls_back_to_default_list():
    recipients = _resolve_recipients(
        default_recipients_raw="equipo@example.com,ops@example.com",
        summary_recipient_email="",
    )

    assert recipients == ["equipo@example.com", "ops@example.com"]
