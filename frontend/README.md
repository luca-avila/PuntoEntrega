# PuntoEntrega Frontend

Frontend React + TypeScript + Vite para el MVP de PuntoEntrega.

## Requisitos

- Node.js + npm
- Backend corriendo en `http://127.0.0.1:8002` (o la URL configurada)

## Variables de entorno

Crear `frontend/.env` (o usar variables exportadas) con:

```env
VITE_API_BASE_URL=http://127.0.0.1:8002
```

Para producción podés partir de `frontend/.env.production.example`.

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
