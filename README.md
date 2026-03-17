# PuntoEntrega

MVP SaaS multi-tenant para registrar entregas/consignaciones por organización.

## Estado del MVP

Implementado:
- Autenticación reutilizando el módulo existente
- Aislamiento por organización en backend
- CRUD de ubicaciones con mapa (Leaflet + OpenStreetMap)
- CRUD de productos con estado activo/inactivo
- Registro de entregas con múltiples ítems
- Historial y detalle de entregas con estado de email

No implementado (fuera de alcance MVP):
- Integraciones de pasarela de pago
- Checkout de suscripción
- Firma digital / remitos / facturación legal
- Optimización de rutas, offline, analytics avanzados

## Requisitos

- Docker + Docker Compose
- Node.js + npm
- `uv` (opcional, para correr backend/tests fuera de Docker)

## Variables de entorno

1. Copiar `.env.example` a `.env`.
2. Completar valores obligatorios (`SECRET_KEY`, `RESEND_API_KEY`, `EMAIL_FROM`, etc.).

Variables relevantes:
- Backend: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SECRET_KEY`, `CORS_ORIGINS`, `FRONTEND_URL`, `RESEND_API_KEY`, `EMAIL_FROM`, `DELIVERY_SUMMARY_RECIPIENTS`
- Frontend: `VITE_API_BASE_URL`

Ejemplo:

```env
DELIVERY_SUMMARY_RECIPIENTS=logistica@empresa.com,facturacion@empresa.com
VITE_API_BASE_URL=http://127.0.0.1:8002
```

## Levantar backend con Docker

```bash
docker compose up --build
```

Backend disponible en `http://127.0.0.1:8002`.

## Levantar frontend (desarrollo)

```bash
cd frontend
npm install
npm run dev
```

Frontend disponible en `http://127.0.0.1:5173`.

## Desarrollo backend local (opcional)

Si preferís correr backend sin contenedor:

```bash
cd backend
uv run alembic upgrade head
uv run uvicorn main:app --reload --port 8002
```

## Tests y checks

Backend:

```bash
cd backend
uv run pytest -q
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

## Regla de email en entregas

Al crear una entrega, primero se persiste en base de datos y luego se intenta enviar email resumen.

- Envío exitoso: `email_status = sent`
- Envío fallido: la entrega se conserva y `email_status = failed`
