# PR A - Ownership + Onboarding Base

## 1) Objetivo del PR

Implementar la base del nuevo flujo de tenancy:

- El registro (`/auth/register`) crea solo el usuario.
- La organizacion se crea manualmente desde un endpoint dedicado.
- El owner se define por `organizations.owner_user_id`.
- `users.role` deja de existir.

Este PR debe dejar el sistema en un estado funcional, sin invitaciones ni peticiones de productos todavia.

## 2) Alcance exacto (in scope)

- Migracion de DB para ownership en `organizations` y eliminacion de `users.role`.
- Cambio de bootstrap aceptado: no se prioriza retrocompatibilidad de datos de desarrollo viejos.
- Refactor del flujo de registro para no crear organizacion automaticamente.
- Endpoint para crear organizacion manualmente (`POST /organizations`).
- Endpoint para consultar organizacion actual (`GET /organizations/current`).
- Ajustes minimos de modelos/schemas/wiring para soportar lo anterior.
- Ajustes de tests backend para el nuevo comportamiento base.

## 3) Fuera de alcance (out of scope)

- Feature de invitaciones.
- Feature de peticiones de productos.
- Cambios de permisos owner/member sobre products/locations/deliveries.
- UI completa de onboarding (queda para PR E segun roadmap).

## 4) Cambios tecnicos detallados

### 4.1 Migracion Alembic

Crear `backend/alembic/versions/0003_organizations_owner_and_drop_user_role.py` con:

1. Agregar columna `organizations.owner_user_id` (UUID, `nullable=False`).
2. Crear FK a `user.id` (ondelete recomendado: `RESTRICT`).
3. Eliminar columna `user.role`.

Contexto explicitado:
- Este PR asume proyecto sin usuarios reales en produccion.
- Si tu base local tiene datos viejos incompatibles, se resetea localmente (no se hace backfill legacy).

Notas de compatibilidad:

- Asegurar soporte SQLite en tests usando `batch_alter_table` donde aplique.
- Mantener migracion clara y simple, sin logica de migracion de datos historicos.

### 4.2 Modelos SQLAlchemy

#### `backend/features/organizations/models.py`

- Agregar `owner_user_id`.
- Agregar relacion `owner`.
- Mantener relacion de usuarios miembros (actualmente `users`) pero desambiguar `foreign_keys` porque ahora habra 2 FKs entre `user` y `organizations`.

#### `backend/features/auth/models.py`

- Eliminar campo `role`.
- Ajustar relacion `organization` con `foreign_keys=[User.organization_id]` para evitar ambiguedad.
- (Opcional, recomendado) agregar relacion inversa `owned_organizations` para claridad.

Importante:

- Resolver explicitamente joins ambiguos por las dos referencias cruzadas:
  - `User.organization_id -> Organization.id`
  - `Organization.owner_user_id -> User.id`

### 4.3 Auth service (registro)

#### `backend/features/auth/service.py`

- Remover logica que hoy crea organizacion en `UserManager.create`.
- El alta de usuario debe:
  - validar password
  - crear usuario con `organization_id = None`
  - commit
  - mantener hooks de verificacion email como estan

- Extraer o mover helper de slug/nombre de organizacion fuera de auth (si se reutiliza en organizations service).

### 4.4 Schemas de auth

#### `backend/features/auth/schemas.py`

- Quitar `role` de `UserRead`.
- Mantener `organization_id` nullable.

Efecto esperado:

- `GET /users/me` y respuesta de registro ya no incluyen `role`.
- En registro, `organization_id` debe venir `null`.

### 4.5 Feature organizations API base

Crear/ajustar:

- `backend/features/organizations/schemas.py` (si no existe)
- `backend/features/organizations/api/routes.py`
- `backend/features/organizations/wiring.py`
- `backend/app/api.py` para incluir router

Endpoints:

1. `POST /organizations`
   - Requiere usuario autenticado activo.
   - Precondicion: `current_user.organization_id is None`.
   - Body minimo: `name`.
   - Crea organizacion + slug unico.
   - Asigna:
     - `organization.owner_user_id = current_user.id`
     - `current_user.organization_id = organization.id`
   - Operacion atomica (una transaccion).
   - Respuestas:
     - `201` exito
     - `409` si usuario ya tiene organizacion
     - `422` input invalido

2. `GET /organizations/current`
   - Requiere usuario con organizacion.
   - Devuelve metadata minima (`id`, `name`, `slug`, `owner_user_id`, `is_active`).
   - `403` si usuario no tiene organizacion.

### 4.6 Service de organizations (base)

En `backend/features/organizations/service.py`:

- Mantener `get_current_organization_id` (ya existe).
- Agregar helper para crear organizacion de usuario:
  - validacion de precondiciones
  - slug unico reutilizando algoritmo actual
  - asignacion owner + membership del usuario
  - commit/rollback seguro

## 5) Ajustes de tests backend

### 5.1 Actualizar tests existentes de auth

Archivo principal: `backend/tests/test_users.py`

- Cambiar expectativa de registro:
  - antes: `organization_id` no null y `role == owner`
  - ahora: `organization_id is null` y sin `role`

### 5.2 Nuevo archivo de tests onboarding

Crear `backend/tests/test_organizations_onboarding.py` con casos:

1. Usuario autenticado sin organizacion puede crear una (`201`).
2. Crear organizacion asigna owner correctamente:
   - `organization.owner_user_id == current_user.id`
   - `current_user.organization_id == organization.id`
3. Usuario con organizacion no puede crear otra (`409`).
4. `GET /organizations/current` devuelve org correcta.
5. Usuario sin organizacion recibe `403` en `GET /organizations/current`.
6. No autenticado recibe `401` en ambos endpoints.

### 5.3 Ajustar helpers compartidos de tests CRUD

Tests de `products`, `locations`, `deliveries` hoy asumen que register crea org.
Actualizar helpers para:

1. registrar usuario
2. verificar email
3. login
4. crear organizacion via `POST /organizations`

Con eso, se preserva el comportamiento actual de esos test files sin tocar permisos aun.

## 6) Verificacion y checks del PR

Ejecutar:

1. (Si aplica) resetear DB local para limpiar datos del esquema viejo.
2. `cd backend && uv run pytest -q`
3. `cd backend && uv run alembic upgrade head` en entorno local de prueba
4. Smoke API manual:
   - register -> users/me (`organization_id = null`)
   - login -> POST /organizations
   - users/me actualizado con `organization_id`
   - GET /organizations/current ok

## 7) Riesgos y mitigaciones

Riesgo: tener DB local con datos viejos y esquema previo.
- Mitigacion: resetear DB local antes de aplicar migracion.

Riesgo: ambiguedad de relaciones SQLAlchemy por doble FK.
- Mitigacion: declarar `foreign_keys` explicitamente en ambos modelos.

Riesgo: romper tests existentes por cambio de bootstrap de tenant.
- Mitigacion: helper comun de setup con creacion de organizacion por API.

## 8) Criterios de aceptacion del PR A

- Registro ya no crea organizacion automaticamente.
- `users.role` eliminado de modelo/esquema/migracion.
- `organizations.owner_user_id` existe y queda poblado/no nulo.
- PR documenta explicitamente que el cambio es de bootstrap (sin estrategia legacy).
- Usuario autenticado sin organizacion puede crear exactamente una organizacion.
- La organizacion creada queda ligada al usuario creador como owner unico.
- Suite backend en verde.

## 9) Secuencia de implementacion sugerida (orden interno)

1. Migracion Alembic + modelos.
2. Refactor de `auth/service.py` (registro).
3. Schemas de auth (`UserRead` sin role).
4. Organizations API + service de creacion manual.
5. Wiring de router.
6. Tests nuevos y ajustes de tests existentes.
7. Run tests + smoke final.
