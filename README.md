# PuntoEntrega

PuntoEntrega es una plataforma para gestionar la operación de entrega y
reposición de productos en locales, sucursales o puntos adheridos.

La aplicación permite organizar usuarios, organizaciones, ubicaciones y
productos; registrar entregas con sus ítems y datos operativos; recibir
solicitudes de productos desde usuarios asociados a una sucursal; y notificar
por email a las personas responsables.

## Problema

En operaciones con múltiples puntos físicos, la reposición de productos suele
quedar repartida entre planillas, mensajes, pedidos informales y confirmaciones
manuales. Eso vuelve difícil saber qué se entregó, dónde, cuándo, por quién y
qué solicitudes siguen pendientes.

PuntoEntrega centraliza ese flujo en una aplicación web interna:

- cada organización administra sus propias ubicaciones, productos y usuarios;
- el dueño de la organización gestiona catálogo, sucursales, entregas e
  invitaciones;
- los usuarios asociados a una sucursal pueden consultar la operación y pedir
  productos;
- las notificaciones operativas se envían por email con trazabilidad y manejo
  de fallas.

## Estado Actual

La app está pensada como software interno en producción, con foco en operación
simple, trazabilidad y mantenimiento claro.

Funcionalidades principales:

- autenticación con registro, verificación de cuenta, login y recuperación de contraseña;
- onboarding de organización posterior al registro;
- modelo multi-tenant con aislamiento por organización;
- dueño de organización y usuarios asociados a una sucursal;
- CRUD de ubicaciones con selección en mapa y geocoding;
- CRUD de productos con estado activo/inactivo;
- registro de entregas con múltiples ítems, fecha, ubicación, pago y observaciones;
- historial y detalle de entregas;
- gestión de equipo e invitaciones por email;
- aceptación pública de invitaciones con token seguro;
- solicitudes de productos desde usuarios asociados a una sucursal;
- notificaciones por email con outbox transaccional y worker dedicado.

Fuera de alcance actual:

- pasarela de pagos;
- checkout de suscripción;
- facturación legal/remitos digitales;
- optimización de rutas;
- funcionamiento offline;
- analytics avanzados.

## Arquitectura

El proyecto usa una arquitectura de modular monolith: un backend FastAPI único,
organizado por features, con una base PostgreSQL compartida y límites claros por
módulo.

```text
React + Vite
   |
   | HTTP / cookies
   v
FastAPI backend
   |
   | SQLAlchemy / Alembic
   v
PostgreSQL
```

El envío de emails no ocurre como efecto secundario directo y frágil dentro del
request principal. Los cambios de negocio y los eventos de notificación se
persisten juntos, y un worker separado procesa los emails.

```text
FastAPI use case
   |
   | same transaction
   v
business tables + notification_outbox
   |
   | polling worker
   v
Resend email provider
```

### Backend

- Python + FastAPI.
- PostgreSQL como base principal.
- SQLAlchemy para persistencia.
- Alembic para migraciones versionadas.
- `uv` como dependency manager.
- Feature-first modules en `backend/features/`.
- Routers finos que delegan reglas y casos de uso a servicios.
- Worker separado para notificaciones.

### Frontend

- React + TypeScript + Vite.
- TailwindCSS y componentes UI locales.
- React Hook Form para formularios.
- API client simple en `frontend/src/api`.
- Rutas protegidas según autenticación, organización y permisos.

## Decisiones Técnicas

- **Modular monolith antes que microservicios.** El dominio todavía entra bien en
  un único deploy backend, con módulos internos claros.
- **Multi-tenancy por organización.** Las entidades operativas cuelgan de una
  organización y las consultas se filtran por ese contexto.
- **Permisos explícitos.** Se distingue entre dueño de organización y usuario
  asociado a sucursal, evitando que el rol viva como un campo global del usuario.
- **Outbox transaccional para emails.** La operación principal no se pierde si
  falla el proveedor de email; el evento queda persistido y procesable.
- **Docker-first para producción.** Backend, worker y base se operan con Docker
  Compose; el frontend se construye como artifact estático para Nginx.
- **Configuración por entorno.** Los valores sensibles y variables de runtime no
  viven hardcodeados en el código.
- **Compatibilidad de rutas públicas.** Las rutas legacy de verificación y reset
  redirigen a las rutas actuales preservando `token`.

## Production-minded features

- **`.env` por contexto.** El proyecto mantiene archivos separados para
  desarrollo, build y runtime para evitar editar manualmente el mismo archivo en
  cada escenario.
- **Config validada al iniciar.** El backend exige variables críticas como
  `DATABASE_URL`, `SECRET_KEY`, `RESEND_API_KEY`, `EMAIL_FROM`, `CORS_ORIGINS` y
  `FRONTEND_URL`.
- **Docker Compose operativo.** PostgreSQL, backend y worker corren como
  servicios separados.
- **Healthchecks.** PostgreSQL usa `pg_isready`; el backend expone `/health` y
  el Dockerfile lo usa como healthcheck.
- **Migraciones automatizadas.** El deploy backend corre `alembic upgrade head`
  antes de recrear backend y worker.
- **Worker dedicado.** Las notificaciones no bloquean la request principal.
- **Retries con backoff.** El outbox reintenta fallas recuperables y marca
  eventos agotados como `failed`.
- **CORS por entorno.** Los orígenes permitidos se configuran desde env vars.
- **Cookies HTTP-only.** La sesión se maneja desde el backend con cookies
  HTTP-only y `secure` en producción.
- **Logging opcional de requests.** `LOG_REQUESTS` permite auditar requests y
  resultados de login.
- **Checks automatizados.** Backend con pytest; frontend con lint y build.

## Variables de Entorno

El archivo `.env.example` documenta los valores esperados. En la práctica el
proyecto mantiene archivos separados según contexto:

- `.env.example`: referencia segura para crear nuevos entornos.
- `.env.development`: runtime local de backend y worker en desarrollo.
- `.env.backend`: runtime del backend/worker en VPS.
- `.env.build`: tags, registry e inputs de build de imágenes.
- `frontend/.env`: variables del dev server de Vite.

Variables relevantes de backend:

- `DATABASE_URL`
- `SECRET_KEY`
- `ENVIRONMENT`
- `LOG_LEVEL`
- `LOG_REQUESTS`
- `CORS_ORIGINS`
- `FRONTEND_URL`
- `RESEND_API_KEY`
- `EMAIL_FROM`
- `NOTIFICATION_WORKER_*`

Variables relevantes de build/frontend:

- `BACKEND_IMAGE_REF`
- `FRONTEND_IMAGE_REF`
- `VITE_API_BASE_URL`
- `VITE_DEV_PROXY_TARGET`
- `VITE_GOOGLE_MAPS_API_KEY`

## Docker

El backend se construye desde `backend/Dockerfile` con `uv sync --frozen
--no-dev`. La misma imagen se usa para dos procesos:

- `backend`: API FastAPI expuesta localmente en `127.0.0.1:8002`.
- `worker`: procesador de outbox de notificaciones.

`docker-compose.yaml` define:

- `db`: PostgreSQL 17 con volumen persistente y healthcheck.
- `backend`: API HTTP.
- `worker`: proceso asincrónico de emails.

El frontend se construye desde `frontend/Dockerfile` como artifact estático. En
producción, Nginx sirve el contenido generado desde `/var/www/PuntoEntrega`.

## Desarrollo Local

Backend con Docker:

```bash
scripts/dev_backend.sh
```

Frontend:

```bash
scripts/dev_frontend.sh
```

O manualmente:

```bash
cd frontend
npm install
npm run dev
```

Backend local sin contenedor:

```bash
cd backend
uv run alembic upgrade head
uv run uvicorn app.api:app --reload --port 8002
```

## Deploy

El flujo de producción está pensado para VPS con Docker Compose + Nginx.

1. Construir imágenes usando `.env.build`.

```bash
scripts/build_images.sh all --push
```

2. Desplegar backend, worker y migraciones.

```bash
sudo scripts/deploy_backend.sh
```

3. Desplegar frontend estático en Nginx.

```bash
sudo scripts/deploy_frontend.sh
```

También existe un wrapper para correr ambos deploys:

```bash
sudo scripts/deploy_production.sh
```

El deploy backend:

- valida la configuración de Compose;
- levanta PostgreSQL;
- espera healthcheck de DB;
- corre Alembic;
- recrea backend y worker;
- valida `/health`;
- muestra logs recientes.

El deploy frontend:

- toma la imagen frontend ya construida;
- extrae `/out/dist`;
- reemplaza el contenido de `/var/www/PuntoEntrega`;
- ajusta permisos para `www-data`;
- valida y recarga Nginx.

## Scripts

- `scripts/dev_backend.sh`: build local de backend, DB, migraciones, backend y worker.
- `scripts/dev_frontend.sh`: Vite dev server con env de frontend.
- `scripts/dev.sh`: backend + frontend en desarrollo.
- `scripts/build_images.sh`: build de imágenes backend/frontend y push opcional.
- `scripts/deploy_backend.sh`: deploy de backend + worker en VPS.
- `scripts/deploy_frontend.sh`: deploy del artifact frontend en Nginx.
- `scripts/deploy_production.sh`: deploy backend + frontend.

## Email Failure Handling

El manejo de emails está diseñado para que una falla del proveedor no rompa la
operación principal.

Cuando una acción necesita email, el backend crea un evento en
`notification_outbox` dentro de la misma transacción que persiste el cambio de
negocio. El worker reclama eventos pendientes, ejecuta el handler
correspondiente y marca el resultado.

Estados del outbox:

- `pending`: evento creado o listo para reintento.
- `processing`: evento reclamado por un worker.
- `processed`: email enviado o handler completado.
- `failed`: evento agotado o no recuperable.

Para solicitudes de productos, la API de historial expone un snapshot derivado del outbox:

- `email_status = pending`
- `email_status = sent`
- `email_status = failed`

El worker usa backoff exponencial, límite de intentos, recuperación de eventos
trabados en `processing` y registro truncado del último error.

## Reglas de Permisos

- **Dueño de organización**
  - crea y edita productos;
  - crea y edita ubicaciones;
  - registra entregas;
  - invita usuarios;
  - consulta historial de entregas y pedidos.
- **Usuario asociado a sucursal**
  - accede a la operación permitida para su organización/sucursal;
  - consulta recursos operativos;
  - solicita productos desde `/productos`;
  - no accede a rutas de administración.

## Flujos Principales

1. Registro -> verificación de cuenta -> login.
2. Creación de organización.
3. Alta de ubicaciones/sucursales.
4. Alta de productos.
5. Invitación de usuarios asociados a una sucursal.
6. Registro de entregas con ítems.
7. Solicitud de productos desde usuario asociado.
8. Notificación por email y seguimiento de estado.

## Verificaciones

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
