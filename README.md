# PuntoEntrega

MVP backend para registrar entregas/consignaciones en un esquema multi-tenant por organización.

## Requisitos

- Docker + Docker Compose
- `uv` (para ejecutar backend y tests localmente sin Docker)

## Variables de entorno

Copiar `.env.example` a `.env` y completar valores.

Variables relevantes:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `SECRET_KEY`
- `RESEND_API_KEY`
- `EMAIL_FROM`
- `DELIVERY_SUMMARY_RECIPIENTS` (lista separada por comas)

Ejemplo:

```env
DELIVERY_SUMMARY_RECIPIENTS=logistica@empresa.com,facturacion@empresa.com
```

## Levantar con Docker Compose

```bash
docker compose up --build
```

Backend disponible en `http://127.0.0.1:8002`.

## Ejecutar tests backend

Desde `backend/`:

```bash
uv run pytest -q
```

## Nota sobre email de entregas

Al crear una entrega, el backend persiste la entrega primero y luego intenta enviar email resumen.

- Si el envío funciona: `email_status = sent`
- Si falla: la entrega se conserva y `email_status = failed`
