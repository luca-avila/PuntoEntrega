# PuntoEntrega Frontend

Frontend React + TypeScript + Vite para el MVP de PuntoEntrega.

## Requisitos

- Node.js + npm
- Backend corriendo en `http://127.0.0.1:8002` (o la URL configurada)

## Variables de entorno

Crear `frontend/.env` (o usar variables exportadas) con:

```env
VITE_API_BASE_URL=/api
VITE_DEV_PROXY_TARGET=http://127.0.0.1:8002
VITE_GOOGLE_MAPS_API_KEY=
```

Notas:
- `VITE_API_BASE_URL=/api` mantiene el frontend alineado con nginx en VPS y evita CORS en desarrollo.
- `VITE_DEV_PROXY_TARGET` define a qué backend reenvía Vite durante desarrollo.
- `VITE_GOOGLE_MAPS_API_KEY` habilita Google Geocoding (si no está, se usa fallback a Nominatim).

Para valores de ejemplo, usá `.env.example` en la raíz del repo.

## Desarrollo

```bash
npm install
npm run dev
```

## Verificaciones

```bash
npm run lint
npm run build
```

## Rutas del cliente web

Públicas:
- `/iniciar-sesion`
- `/registro`
- `/recuperar-contrasena`
- `/restablecer-contrasena`
- `/verificar-email`
- `/aceptar-invitacion?token=...`

Aliases legacy con redirección a rutas en español:
- `/reset-password` -> `/restablecer-contrasena`
- `/verify-email` -> `/verificar-email`

Protegidas para usuario autenticado:
- `/`
- `/organizacion/crear`
- `/onboarding/organizacion` (alias legacy que redirige a `/organizacion/crear`)

Protegidas con organización:
- `/entregas`
- `/entregas/:deliveryId`
- `/ubicaciones`
- `/productos`

Owner-only:
- `/equipo`
- `/entregas/nueva`
- `/ubicaciones/nueva`
- `/ubicaciones/:locationId/editar`
- `/productos/nuevo`
- `/productos/:productId/editar`

## Comportamiento por rol

- usuario autenticado sin organización:
  - puede entrar a `Inicio` y crear una organización cuando lo necesite.
  - ve acceso directo a `Crear organización` desde navegación.
  - al intentar entrar a módulos operativos (`/entregas`, `/ubicaciones`, `/productos`) se redirige a `/organizacion/crear`.
- `owner`: ve navegación completa (`Nueva entrega`, `Equipo`) y acciones de alta/edición.
- `member`: ve solo navegación y acciones permitidas de lectura/operación compartida.
- si un `member` intenta entrar manualmente por URL a una ruta owner-only, el guard redirige a `/`.

## Onboarding y contexto organizacional

- usuario autenticado sin `organization_id`:
  - no queda bloqueado al iniciar sesión.
  - puede crear organización cuando quiera desde `/organizacion/crear`.
  - al crearla pasa a operar con permisos de owner.
- usuario con organización:
  - no vuelve a onboarding y entra al flujo operativo normal.

## Flujo de invitación y retorno de login

- la pantalla de aceptación de invitación arma un `next` al path actual (`/aceptar-invitacion?token=...`).
- login conserva `next` para volver al flujo luego de autenticarse.
- `next` se valida como ruta interna para evitar redirecciones inválidas.

## Checklist manual sugerido

1. Owner:
   - ve `Nueva entrega` y `Equipo` en nav.
   - puede crear/editar ubicaciones y productos.
2. Member:
   - no ve CTAs owner-only en Home, Ubicaciones, Historial y detalle.
   - acceso directo por URL a rutas owner-only redirige a `/`.
3. Usuario autenticado sin organización:
   - puede iniciar sesión y ver inicio sin bloqueo.
   - puede crear organización desde `/organizacion/crear`.
4. Invitación:
   - abrir `/aceptar-invitacion?token=...` sin sesión.
   - iniciar sesión desde el CTA.
   - volver automáticamente al flujo de aceptación.

## Documentación visual

- Guía del sistema visual: `frontend/docs/visual-system.md`
