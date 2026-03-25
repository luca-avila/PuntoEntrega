# PR E - Frontend Onboarding + Ownership Context

## 1) Objetivo del PR

Implementar en frontend el onboarding de organización y el contexto de ownership para soportar el nuevo flujo:

- Usuario se registra/inicia sesión sin organización.
- Si no tiene organización, debe ir a onboarding (`/onboarding/organizacion`).
- Si ya tiene organización, accede al resto de rutas protegidas.
- El frontend debe conocer la organización actual y si el usuario es owner para siguientes PRs.

Este PR debe dejar la base funcional de navegación y contexto para owner/member sin incluir todavía UI de invitaciones ni solicitudes de productos.

## 2) Alcance exacto (in scope)

- Nueva pantalla de onboarding de organización.
- Guard global de rutas para bloquear flujo de negocio sin organización.
- Contratos/API frontend para organizaciones (`POST /organizations`, `GET /organizations/current`).
- Extensión del contexto de autenticación para exponer organización actual + ownership.
- Ajustes de copy/flujo en pantallas de auth para reflejar onboarding posterior al login.

## 3) Fuera de alcance (out of scope)

- UI de equipo e invitaciones (`/equipo`).
- UI pública de aceptación de invitación.
- UI de product requests en `/productos`.
- Cambios backend adicionales.

## 4) Cambios técnicos detallados

### 4.1 Contratos y API frontend

Crear:

1. `frontend/src/api/contracts/organizations.ts`
   - `OrganizationCreate` (`name`).
   - `OrganizationRead` (`id`, `name`, `slug`, `owner_user_id`, `is_active`).

2. `frontend/src/api/organizations-api.ts`
   - `create(payload)` -> `POST /organizations`
   - `getCurrent()` -> `GET /organizations/current`

Actualizar:

1. `frontend/src/api/contracts/auth.ts`
   - remover `role` de `SessionUser` (ya no existe en backend).
   - mantener `organization_id: string | null`.

2. `frontend/src/api/contracts/index.ts` y `frontend/src/api/index.ts`
   - exportar contratos/API de organizaciones.

### 4.2 Contexto de ownership

Actualizar `frontend/src/features/auth/auth-context-store.ts` y `auth-context.tsx` para exponer:

- `organization: OrganizationRead | null`
- `isOwner: boolean`
- `refreshOrganization(): Promise<void>`

Comportamiento esperado:

1. Luego de `refreshSession`, si `user.organization_id` es `null`:
   - `organization = null`
   - `isOwner = false`

2. Si `user.organization_id` existe:
   - cargar `organizationsApi.getCurrent()`
   - `isOwner = organization.owner_user_id === user.id`

3. En `logout` o `401`:
   - limpiar `user`, `organization` e `isOwner`.

Objetivo:
- tener ownership disponible globalmente para PR F sin duplicar lógica por pantalla.

### 4.3 Pantalla onboarding

Crear `frontend/src/pages/organization-onboarding-page.tsx`:

- Formulario simple con React Hook Form:
  - `name` obligatorio, trim.
- Submit a `organizationsApi.create`.
- En éxito:
  - refrescar auth/context (`refreshSession` y/o `refreshOrganization`)
  - redirigir a `/`.
- Manejo de errores API consistente con mensajes amigables.

UX mínima:
- usar componentes existentes (`Card`, `Input`, `Button`, `Label`).
- texto orientado a “crear tu organización para continuar”.

### 4.4 Guard global de rutas

Implementar guard para organización dentro del flujo protegido:

1. Si no autenticado -> `/iniciar-sesion` (comportamiento actual).
2. Si autenticado y `organization_id === null`:
   - permitir solo `/onboarding/organizacion`
   - redirigir cualquier otra ruta protegida a onboarding.
3. Si autenticado y ya tiene organización:
   - redirigir `/onboarding/organizacion` hacia `/`.

Aplicar en `frontend/src/App.tsx` usando `ProtectedRoute` y un guard adicional (componente nuevo o extensión del actual).

### 4.5 Ruteo y flujo de navegación

Actualizar `frontend/src/App.tsx`:

- agregar ruta protegida `/onboarding/organizacion`.
- mantener el resto de rutas de negocio detrás del guard de organización.

Ajustar textos en auth:

- `register-page.tsx`: reflejar que primero se crea cuenta y luego organización.
- `login-page.tsx`: mantener redirección normal, pero el guard decidirá onboarding vs app.

## 5) Verificación y checks del PR

Ejecutar:

1. `cd frontend && npm run lint`
2. `cd frontend && npm run build`

Smoke manual:

1. Usuario nuevo:
   - registro + login -> redirección a `/onboarding/organizacion`.
2. Crear organización:
   - submit exitoso -> redirección a `/`.
3. Usuario con organización:
   - login -> entra a `/` sin pasar por onboarding.
4. Intento manual de entrar a `/onboarding/organizacion` con org creada:
   - redirección a `/`.
5. Logout:
   - vuelve a estado no autenticado.

## 6) Riesgos y mitigaciones

Riesgo: bucles de redirección entre rutas protegidas y onboarding.
- Mitigación: centralizar reglas de redirección en un único guard.

Riesgo: estado inconsistente entre `user.organization_id` y `organizations/current`.
- Mitigación: refrescar organización desde backend al iniciar sesión y luego de crear organización.

Riesgo: UI futura replique lógica owner/member.
- Mitigación: exponer `isOwner` desde contexto compartido.

## 7) Criterios de aceptación del PR E

- Existe pantalla funcional `/onboarding/organizacion`.
- Usuario autenticado sin organización no puede usar rutas de negocio.
- Crear organización desde onboarding redirige correctamente al home.
- `SessionUser` en frontend no usa `role`.
- Contexto frontend expone organización actual e `isOwner`.
- `lint` y `build` de frontend en verde.

## 8) Secuencia de implementación sugerida (orden interno)

1. Contratos/API de organizaciones + ajuste de contrato auth.
2. Extender contexto auth con organización e `isOwner`.
3. Crear página de onboarding.
4. Implementar guard de organización y actualizar rutas.
5. Ajustes de copy en auth pages.
6. Lint/build + smoke final.
