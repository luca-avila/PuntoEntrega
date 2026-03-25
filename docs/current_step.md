# PR F - Frontend Equipo/Invitaciones + Aceptación Pública + Solicitud de Productos

## 1) Objetivo del PR

Implementar en frontend los flujos funcionales que consumen las features backend ya cerradas en PR C y PR D:

- Gestión de equipo e invitaciones (owner).
- Aceptación pública de invitación por token.
- Solicitud de productos desde la pantalla de productos (member).

Este PR debe dejar la experiencia end-to-end utilizable sin agregar nuevas reglas backend.

## 2) Alcance exacto (in scope)

- Nueva ruta `/equipo` para owner:
  - listado de miembros (`GET /organization-members`)
  - formulario de invitación (`POST /organization-invitations`)
  - listado de invitaciones (`GET /organization-invitations`)
  - cancelar invitación (`POST /organization-invitations/{id}/cancel`)
- Nueva página pública `/aceptar-invitacion`:
  - validación token (`GET /organization-invitations/accept-info`)
  - aceptación con cuenta nueva (`POST /organization-invitations/accept`)
  - aceptación autenticada (`POST /organization-invitations/accept-authenticated`)
- Integración de solicitud de productos en `/productos` para member:
  - formulario simple asunto + mensaje
  - alta via `POST /product-requests`
- Contratos y API clients frontend para invitations/product-requests/organization-members.

## 3) Fuera de alcance (out of scope)

- Rework visual profundo del layout general.
- Nuevos permisos backend o cambios de negocio.
- Auditoría frontend completa de product requests para owner (queda para PR posterior si se necesita vista dedicada).
- Cambios de infraestructura/testing E2E automatizado.

## 4) Cambios técnicos detallados

### 4.1 API y contratos frontend

Crear:

1. `frontend/src/api/contracts/invitations.ts`
   - `OrganizationInvitationCreate`
   - `OrganizationInvitationRead`
   - `OrganizationInvitationAcceptInfoRead`
   - `OrganizationInvitationAcceptCreate`
   - `OrganizationInvitationAcceptAuthenticated`
   - `OrganizationInvitationAcceptResult`

2. `frontend/src/api/invitations-api.ts`
   - `create`, `list`, `cancel`
   - `getAcceptInfo`
   - `acceptNewAccount`
   - `acceptAuthenticated`

3. `frontend/src/api/contracts/product-requests.ts`
   - `ProductRequestCreate`
   - `ProductRequestRead`

4. `frontend/src/api/product-requests-api.ts`
   - `create`
   - (opcional helper `list` para uso futuro owner)

5. `frontend/src/api/contracts/organization-members.ts`
   - `OrganizationMemberRead`

6. `frontend/src/api/organization-members-api.ts`
   - `list`

Actualizar exports de `api/index.ts` y `api/contracts/index.ts`.

### 4.2 Pantalla `/equipo` (owner)

Crear `frontend/src/pages/team-page.tsx`:

- Sección 1: miembros actuales (owner + members), usando `organization-members-api`.
- Sección 2: invitar por email:
  - React Hook Form (`email`)
  - submit a `invitationsApi.create`
  - feedback de éxito/error.
- Sección 3: invitaciones:
  - listado con estado (`pending|accepted|expired|cancelled`)
  - acción “Cancelar” solo para `pending`.

Permisos frontend:
- mostrar acceso a `/equipo` solo si `isOwner`.
- si no owner, redirigir a `/`.

### 4.3 Aceptación pública `/aceptar-invitacion`

Crear `frontend/src/pages/accept-invitation-page.tsx`:

- Leer `token` desde query string.
- Cargar `accept-info`.
- Estados de pantalla:
  - token inválido / expirado / cancelado / aceptado.
  - token válido.
- Si válido:
  - Cuenta nueva: formulario contraseña + confirmar, POST `/accept`.
  - Cuenta existente:
    - si no autenticado: CTA a login preservando retorno.
    - si autenticado: botón aceptar autenticada (POST `/accept-authenticated`).
- Mostrar mensajes backend de conflicto (email no coincide, usuario ya en org, etc.).

### 4.4 Solicitud de productos (member)

Actualizar `frontend/src/pages/products-list-page.tsx`:

- Si `isOwner`:
  - mantener comportamiento actual (alta/edición).
- Si `!isOwner`:
  - ocultar CTA de “Nuevo producto” y acciones de edición.
  - mostrar bloque “Solicitar producto” con formulario:
    - `subject` (max 255)
    - `message` (mínimo 10)
  - submit a `productRequestsApi.create`.
  - feedback de envío y errores.

### 4.5 Navegación y accesos

Actualizar:

- `frontend/src/App.tsx`:
  - ruta protegida `/equipo` (owner).
  - ruta pública `/aceptar-invitacion`.
- `frontend/src/components/layout/protected-layout.tsx`:
  - agregar nav item “Equipo” solo para owner.

## 5) Verificación y checks del PR

Ejecutar:

1. `cd frontend && npm run lint`
2. `cd frontend && npm run build`

Smoke manual:

1. Owner:
   - entra a `/equipo`
   - invita email
   - ve invitación en listado
   - cancela invitación pending
2. Invitado:
   - abre `/aceptar-invitacion?token=...`
   - valida estado
   - acepta con cuenta nueva y con cuenta autenticada
3. Member:
   - entra a `/productos`
   - ve formulario de solicitud y puede enviar
4. Owner:
   - no ve formulario member en `/productos`

## 6) Riesgos y mitigaciones

Riesgo: incoherencia entre permisos backend y UI visible.
- Mitigación: usar `isOwner` del `AuthContext` para visibilidad de acciones y rutas.

Riesgo: UX confusa en aceptación con login intermedio.
- Mitigación: preservar `token` en query y redirigir de vuelta al flujo público.

Riesgo: errores de API no claros para el usuario final.
- Mitigación: mapear `detail` del backend y mostrar feedback contextual en cada formulario.

## 7) Criterios de aceptación del PR F

- Owner puede gestionar miembros e invitaciones desde `/equipo`.
- Flujo de `/aceptar-invitacion` funciona para token válido e inválido.
- Aceptación con cuenta nueva y autenticada disponibles en UI.
- Member puede solicitar productos desde `/productos`.
- Owner no ve acciones de member en `/productos`.
- `lint` y `build` frontend en verde.

## 8) Secuencia de implementación sugerida (orden interno)

1. API contracts + clients (invitations/product-requests/members).
2. Página `/equipo` con invitaciones.
3. Página pública `/aceptar-invitacion`.
4. Integración solicitud member en `/productos`.
5. Rutas/nav y controles por owner/member.
6. Lint/build + smoke final.
