# PuntoEntrega

MVP SaaS multi-tenant para registrar entregas/consignaciones por organización.

## Estado del MVP

Implementado:
- Autenticación reutilizando el módulo existente
- Onboarding de organización (creación manual post-login)
- Modelo owner/member (sin `role` en usuario)
- Aislamiento por organización en backend
- CRUD de ubicaciones con mapa (Leaflet + OpenStreetMap)
- CRUD de productos con estado activo/inactivo
- Registro de entregas con múltiples ítems
- Historial y detalle de entregas con estado de email
- Gestión de equipo e invitaciones por email (owner)
- Aceptación pública de invitaciones con token seguro
- Solicitud de productos por members (notificación por email al owner)

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
- Backend: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SECRET_KEY`, `CORS_ORIGINS`, `FRONTEND_URL`, `RESEND_API_KEY`, `EMAIL_FROM`
- Frontend: `VITE_API_BASE_URL`, `VITE_DEV_PROXY_TARGET` (solo desarrollo), `VITE_GOOGLE_MAPS_API_KEY` (opcional para geocoding preciso)

Ejemplo:

```env
VITE_API_BASE_URL=/api
VITE_DEV_PROXY_TARGET=http://127.0.0.1:8002
VITE_GOOGLE_MAPS_API_KEY=
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

## Reglas de permisos (resumen)

- `owner`:
  - alta/edición de productos, ubicaciones y entregas.
  - acceso a `/equipo` para gestionar miembros e invitaciones.
- `member`:
  - acceso de lectura a recursos operativos.
  - puede solicitar productos desde `/productos`.
  - no tiene acceso a rutas owner-only.

## Flujos funcionales clave

1. Registro -> login -> onboarding (`/onboarding/organizacion`) -> app.
2. Owner invita miembro desde `/equipo`.
3. Invitado acepta por `/aceptar-invitacion?token=...` (cuenta nueva o autenticada).
4. Member solicita producto desde `/productos`.
5. Owner recibe email de solicitud y puede auditar requests por backend.

## Regla de email en entregas

Al crear una entrega, primero se persiste en base de datos y luego se intenta enviar email resumen.

- Envío exitoso: `email_status = sent`
- Envío fallido: la entrega se conserva y `email_status = failed`
