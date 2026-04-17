from core.frontend_urls import build_frontend_action_url
from features.notifications.errors import EmailSendError
from features.notifications.email_provider import send_email

# Keep Spanish routes in outgoing emails for backward compatibility with
# older frontend deployments that may not include the English aliases yet.
VERIFY_EMAIL_PATH = "/verificar-email"
RESET_PASSWORD_PATH = "/restablecer-contrasena"


def _build_verify_email_html(verify_url: str) -> str:
    return (
        "<p>Hola,</p>"
        "<p>Gracias por registrarte en PuntoEntrega.</p>"
        "<p>Para activar tu cuenta, hac&eacute; click en el siguiente enlace:</p>"
        f"<p><a href=\"{verify_url}\">{verify_url}</a></p>"
        "<p>Si no creaste esta cuenta, pod&eacute;s ignorar este mensaje.</p>"
        "<p>&mdash; Equipo PuntoEntrega</p>"
    )


def _build_reset_password_email_html(reset_url: str) -> str:
    return (
        "<p>Hola,</p>"
        "<p>Recibimos una solicitud para restablecer tu contrase&ntilde;a en PuntoEntrega.</p>"
        "<p>Para crear una nueva contrase&ntilde;a, hac&eacute; click en el siguiente enlace:</p>"
        f"<p><a href=\"{reset_url}\">{reset_url}</a></p>"
        "<p>Si no solicitaste este cambio, pod&eacute;s ignorar este mensaje.</p>"
        "<p>&mdash; Equipo PuntoEntrega</p>"
    )


async def send_verify_email(to_email: str, token: str) -> None:
    try:
        verify_url = build_frontend_action_url(VERIFY_EMAIL_PATH, token)
    except ValueError as exc:
        raise EmailSendError(f"Invalid verification URL config: {exc}") from exc

    await send_email(
        to_email=to_email,
        subject="Activa tu cuenta de PuntoEntrega",
        html=_build_verify_email_html(verify_url),
    )


async def send_reset_password_email(to_email: str, token: str) -> None:
    try:
        reset_url = build_frontend_action_url(RESET_PASSWORD_PATH, token)
    except ValueError as exc:
        raise EmailSendError(f"Invalid reset-password URL config: {exc}") from exc

    await send_email(
        to_email=to_email,
        subject="Restablece tu clave de PuntoEntrega",
        html=_build_reset_password_email_html(reset_url),
    )
