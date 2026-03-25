from urllib.parse import urlencode

from core.config import settings
from core.errors import EmailSendError
from features.auth.email import _normalize_frontend_base_url, _send_email

INVITATION_ACCEPT_PATH = "/aceptar-invitacion"


def _build_invitation_accept_url(token: str) -> str:
    frontend_base = _normalize_frontend_base_url(settings.FRONTEND_URL)
    return f"{frontend_base}{INVITATION_ACCEPT_PATH}?{urlencode({'token': token})}"


def _build_invitation_email_html(
    organization_name: str,
    accept_url: str,
) -> str:
    return (
        "<p>Hola,</p>"
        f"<p>Te invitaron a unirte a <strong>{organization_name}</strong> en PuntoEntrega.</p>"
        "<p>Para aceptar la invitación, hacé click en el siguiente enlace:</p>"
        f"<p><a href=\"{accept_url}\">{accept_url}</a></p>"
        "<p>Si no esperabas esta invitación, podés ignorar este mensaje.</p>"
        "<p>&mdash; Equipo PuntoEntrega</p>"
    )


async def send_organization_invitation_email(
    to_email: str,
    organization_name: str,
    token: str,
) -> None:
    try:
        accept_url = _build_invitation_accept_url(token)
    except ValueError as exc:
        raise EmailSendError(f"Invalid invitation URL config: {exc}") from exc

    await _send_email(
        to_email=to_email,
        subject=f"Invitación a {organization_name} en PuntoEntrega",
        html=_build_invitation_email_html(organization_name, accept_url),
    )
