# PR G - Documentación Final y Hardening

## 1) Objetivo del PR

Cerrar el ciclo del MVP con:

- hardening de frontend para alinear navegación/rutas con permisos owner/member.
- documentación final de flujos implementados y guía de verificación.

Este PR no agrega features nuevas de negocio; consolida experiencia, seguridad operativa y claridad de uso.

## 2) Alcance exacto (in scope)

- Endurecer rutas frontend owner-only para evitar acceso por URL a pantallas de alta/edición.
- Ajustar visibilidad de acciones CTA en UI según `isOwner`.
- Mejorar navegación inicial para member (sin acciones de escritura no permitidas).
- Actualizar documentación principal (`README` raíz y `frontend/README`) con estado real del producto y flujos owner/member.
- Mantener `lint` y `build` frontend en verde.

## 3) Fuera de alcance (out of scope)

- Nuevos endpoints backend o cambios de esquema.
- Refactor visual amplio del diseño.
- Tests E2E automáticos.
- Nuevos módulos funcionales fuera de los PRs A-F.

## 4) Cambios técnicos detallados

### 4.1 Hardening de rutas owner-only

Actualizar `frontend/src/App.tsx` para que queden bajo `OwnerOnlyRoute`:

- `/equipo`
- `/entregas/nueva`
- `/ubicaciones/nueva`
- `/ubicaciones/:locationId/editar`
- `/productos/nuevo`
- `/productos/:productId/editar`

Mantener rutas compartidas owner/member:

- `/`
- `/entregas`
- `/entregas/:deliveryId`
- `/ubicaciones`
- `/productos`

### 4.2 Hardening de UI por rol

Actualizar páginas y layout para consistencia con permisos backend:

- `ProtectedLayout`:
  - member no ve `Nueva entrega`.
  - owner sí ve `Nueva entrega` y `Equipo`.
- `HomePage`:
  - quick actions diferenciadas por rol.
- `LocationsListPage`:
  - member no ve botones crear/editar.
- `DeliveriesHistoryPage`:
  - member no ve CTA de nueva entrega en estado vacío.

### 4.3 Hardening de navegación de login

Conservar comportamiento de `next` para flujos que requieren login intermedio (por ejemplo aceptación de invitación), evitando perder contexto de retorno.

### 4.4 Documentación final

Actualizar:

1. `README.md` (raíz)
   - estado actual implementado (onboarding, ownership, invitaciones, product requests).
   - resumen de permisos owner/member.
   - flujo funcional esperado punta a punta.

2. `frontend/README.md`
   - rutas clave públicas/protegidas.
   - comportamiento onboarding y rol en frontend.
   - checklist de validación manual del cliente web.

## 5) Verificación y checks del PR

Ejecutar:

1. `cd frontend && npm run lint`
2. `cd frontend && npm run build`

Smoke manual:

1. owner:
   - ve nav completa (`Nueva entrega`, `Equipo`) y puede acceder a rutas owner-only.
2. member:
   - no ve acciones owner-only en navegación y pantalla.
   - acceso manual por URL a rutas owner-only redirige a `/`.
3. invitación:
   - login con `next` mantiene retorno al flujo de aceptación.

## 6) Riesgos y mitigaciones

Riesgo: UX inconsistente entre pantallas (botones visibles pero acción bloqueada).
- Mitigación: alinear visibilidad UI y guards de rutas por `isOwner`.

Riesgo: regresiones de navegación al endurecer rutas.
- Mitigación: smoke manual enfocado en rutas owner/member y build tipado.

Riesgo: documentación desactualizada respecto al código.
- Mitigación: actualizar docs en el mismo PR de hardening.

## 7) Criterios de aceptación del PR G

- Rutas owner-only protegidas en frontend.
- UI no muestra acciones de escritura a members donde no corresponda.
- Flujo de login con retorno (`next`) funcional.
- Documentación raíz y frontend alineada al estado real del producto.
- `lint` y `build` frontend en verde.

## 8) Secuencia de implementación sugerida (orden interno)

1. Hardening de routes en `App.tsx`.
2. Ajustes de visibilidad por rol en layout/pages.
3. Revisión de retorno de login y navegación.
4. Actualización de documentación final.
5. Lint/build + smoke final.
