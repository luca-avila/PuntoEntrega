# Guía de Sistema Visual

Esta guía define el sistema visual base de PuntoEntrega para mantener una UI consistente, simple y legible.

## Objetivo

- Tema oscuro por defecto.
- Mayor jerarquía visual.
- Separación clara entre secciones y bloques.
- Componentes reutilizables con el mismo lenguaje visual.

## Fuente de verdad

- Tokens globales: `frontend/src/index.css`
- Extensiones Tailwind: `frontend/tailwind.config.js`
- Componentes base: `frontend/src/components/ui/*`

## 1) Colores base

Los colores se definen con variables CSS (`:root`) y se consumen con clases de Tailwind (`bg-background`, `bg-card`, etc.).

- `background`: fondo general de la app.
- `card`: fondo de tarjetas y contenedores.
- `border`: borde estándar.
- `primary`: acción principal (CTA).
- `secondary`: fondo para acciones secundarias o bloques suaves.
- `muted` y `muted-foreground`: texto y superficies de menor énfasis.
- `destructive`: errores o acciones destructivas.

Regla: nunca hardcodear colores (`bg-slate-*`, `text-gray-*`, etc.) en pantallas nuevas. Usar siempre tokens.

## 2) Tipografía

- Títulos: `font-heading` (Manrope).
- Texto base: `font-body`.
- Jerarquía reusable:
  - `page-title` para título principal de pantalla.
  - `page-description` para subtítulo/contexto.
  - `CardTitle` para títulos de bloques.

Regla: usar la jerarquía existente y evitar tamaños arbitrarios por pantalla.

## 3) Spacing estándar

- `page-section`: separación vertical principal entre bloques de pantalla.
- `page-header`: agrupación título + subtítulo.
- Formularios: mantener `space-y-4` o `space-y-5` según densidad.
- Grillas de campos: `gap-4` como base.

Regla: priorizar estos patrones antes de inventar nuevos.

## 4) Botones

Componente: `Button` (`frontend/src/components/ui/button.tsx`)

- `variant="primary"` o default:
  - Acción principal de la vista (guardar, crear, enviar).
- `variant="secondary"`:
  - Acción secundaria visible.
- `variant="outline"`:
  - Acciones auxiliares (cancelar, volver, editar contextual).
- `variant="ghost"`:
  - Acciones de bajo peso visual.

Regla: cada pantalla debe tener una sola acción principal destacada por contexto.

## 5) Inputs

Componentes:

- `Input`
- `Select`
- `Textarea`
- `Label`

Todos usan fondo oscuro, borde estándar y foco con `ring` del tema.

Regla: no crear inputs con clases inline distintas si no hay motivo funcional real.

## 6) Cards y contenedores

Componente: `Card` (`frontend/src/components/ui/card.tsx`)

- `Card`: contenedor base con borde + shadow + radio grande.
- `CardHeader`, `CardContent`, `CardFooter`: estructura estándar.

Regla: usar card para separar bloques funcionales (filtros, listados, formularios, estados vacíos).

## 7) Estados y feedback

Utilidades globales en `index.css`:

- `feedback-success`: mensajes de éxito.
- `feedback-error`: mensajes de error.
- `status-chip`, `status-chip-success`, `status-chip-danger`, `status-chip-muted`: badges/estados.

Regla: no repetir estilos de alertas/badges con clases ad hoc por pantalla.

## 8) Layout de pantalla

- `app-shell`: layout general autenticado.
- `auth-shell`: pantallas de autenticación.
- Header principal y navegación ya estilizados en `ProtectedLayout`.

Regla: construir nuevas páginas sobre estos shells y utilidades existentes.

## Checklist para pantallas nuevas

1. Estructurar pantalla con `page-section`.
2. Encabezado con `page-title` + `page-description`.
3. Bloques funcionales dentro de `Card`.
4. Usar `Button` variants del sistema.
5. Usar `Input/Select/Textarea/Label` del sistema.
6. Mostrar errores y éxito con `feedback-error`/`feedback-success`.
7. No hardcodear colores fuera de tokens.
