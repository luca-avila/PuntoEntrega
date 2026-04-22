from core.frontend_urls import build_frontend_action_url
from features.notifications.errors import EmailSendError
from features.notifications.email_provider import send_email

__all__ = [
    "send_account_verification_email",
    "send_password_reset_email",
    "send_verify_email",
    "send_reset_password_email",
]

ACCOUNT_VERIFICATION_PATH = "/verificar-email"
PASSWORD_RESET_PATH = "/restablecer-contrasena"


def _build_account_verification_email_html(verification_url: str) -> str:
    return (
        "<p>Hola,</p>"
        "<p>Gracias por registrarte en PuntoEntrega.</p>"
        "<p>Para activar tu cuenta, hac&eacute; click en el siguiente enlace:</p>"
        f"<p><a href=\"{verification_url}\">{verification_url}</a></p>"
        "<p>Si no creaste esta cuenta, pod&eacute;s ignorar este mensaje.</p>"
        "<p>&mdash; Equipo PuntoEntrega</p>"
    )


def _build_password_reset_email_html(password_reset_url: str) -> str:
    return (
        "<p>Hola,</p>"
        "<p>Recibimos una solicitud para restablecer tu contrase&ntilde;a en PuntoEntrega.</p>"
        "<p>Para crear una nueva contrase&ntilde;a, hac&eacute; click en el siguiente enlace:</p>"
        f"<p><a href=\"{password_reset_url}\">{password_reset_url}</a></p>"
        "<p>Si no solicitaste este cambio, pod&eacute;s ignorar este mensaje.</p>"
        "<p>&mdash; Equipo PuntoEntrega</p>"
    )


async def send_account_verification_email(to_email: str, token: str) -> None:
    try:
        verification_url = build_frontend_action_url(ACCOUNT_VERIFICATION_PATH, token)
    except ValueError as exc:
        raise EmailSendError(f"Invalid account verification URL config: {exc}") from exc

    await send_email(
        to_email=to_email,
        subject="Activa tu cuenta de PuntoEntrega",
        html=_build_account_verification_email_html(verification_url),
    )


async def send_password_reset_email(to_email: str, token: str) -> None:
    try:
        password_reset_url = build_frontend_action_url(PASSWORD_RESET_PATH, token)
    except ValueError as exc:
        raise EmailSendError(f"Invalid password reset URL config: {exc}") from exc

    await send_email(
        to_email=to_email,
        subject="Restablece tu clave de PuntoEntrega",
        html=_build_password_reset_email_html(password_reset_url),
    )


# Backward-compatible names used by older imports.
async def send_verify_email(to_email: str, token: str) -> None:
    await send_account_verification_email(to_email, token)


async def send_reset_password_email(to_email: str, token: str) -> None:
    await send_password_reset_email(to_email, token)
