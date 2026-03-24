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

`VITE_API_BASE_URL=/api` mantiene el frontend alineado con nginx en VPS y evita CORS en desarrollo (el navegador llama a `/api` en el servidor de Vite).
`VITE_DEV_PROXY_TARGET` define a qué backend reenvía Vite durante desarrollo.
`VITE_GOOGLE_MAPS_API_KEY` habilita Google Geocoding para mejor precisión de dirección/altura (si no está, se usa fallback a Nominatim).

Para Google Geocoding:
- habilitá Geocoding API en Google Cloud
- restringí la key por HTTP referrer (dominios de dev/prod)

Para producción podés partir de `frontend/.env.production.example`.
Para desarrollo podés partir de `frontend/.env.development.example`.

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

## Documentación visual

- Guía del sistema visual: `frontend/docs/visual-system.md`
