# PR B - Owner/Member Authorization Base

## 1) Objetivo del PR

Implementar la capa de autorizacion owner/member sobre el modelo nuevo de ownership:

- El owner se define exclusivamente por `organizations.owner_user_id`.
- No existe `users.role`.
- Los endpoints operativos existentes deben aplicar permisos por tipo de usuario (owner o member).

Este PR debe dejar permisos backend claros y consistentes, sin incluir todavia invitaciones ni peticiones de productos.

## 2) Alcance exacto (in scope)

- Agregar dependencias reutilizables de autorizacion en `features/organizations/service.py`.
- Exponer endpoint para listar miembros de la organizacion actual (solo owner).
- Ajustar permisos en endpoints existentes de `products`, `locations` y `deliveries`.
- Mantener routers finos (sin logica de negocio en handlers).
- Ajustar tests backend para validar matriz de permisos owner/member.

## 3) Fuera de alcance (out of scope)

- Feature de invitaciones por email.
- Feature de peticiones de productos.
- Cambios de frontend.
- Co-owners o permisos granulares avanzados.

## 4) Cambios tecnicos detallados

### 4.1 Dependencias de autorizacion reutilizables

En `backend/features/organizations/service.py`, agregar:

1. `get_current_user_with_optional_organization`
   - retorna usuario autenticado activo
   - no exige `organization_id`

2. `get_current_user_with_organization`
   - exige `organization_id` no nulo
   - valida que la organizacion exista y este activa
   - retorna usuario + organizacion actual

3. `require_organization_owner`
   - depende de `get_current_user_with_organization`
   - valida `organization.owner_user_id == current_user.id`
   - si no cumple: `403`

4. `require_organization_member`
   - depende de `get_current_user_with_organization`
   - valida usuario con organizacion y `organization.owner_user_id != current_user.id`
   - si no cumple: `403`

5. `require_organization_user`
   - owner o member (usuario con organizacion valida)
   - utilidad para endpoints de lectura

Notas:
- Reusar mensajes de error claros y consistentes.
- Evitar duplicar queries de organizacion innecesariamente.

### 4.2 Endpoint de miembros de organizacion

Crear en `backend/features/organizations/api/routes.py`:

- `GET /organization-members`
  - requiere owner
  - lista usuarios de su organizacion actual
  - campos minimos por item: `id`, `email`, `is_active`, `is_verified`, `created_at`

Agregar/ajustar schemas en `backend/features/organizations/schemas.py` para la respuesta.

### 4.3 Ajustes de permisos en endpoints existentes

Aplicar dependencia correcta por endpoint:

#### Products
- `GET /products` y `GET /products/{id}`: `require_organization_user`
- `POST /products` y `PATCH /products/{id}`: `require_organization_owner`

#### Locations
- `GET /locations` y `GET /locations/{id}`: `require_organization_user`
- `POST /locations` y `PATCH /locations/{id}`: `require_organization_owner`

#### Deliveries
- `GET /deliveries` y `GET /deliveries/{id}`: `require_organization_user`
- `POST /deliveries`: `require_organization_owner`

Importante:
- Mantener aislamiento multi-tenant actual.
- No mover reglas de dominio a routers; solo control de acceso en capa dependencia/entrada.

### 4.4 Migraciones

- Este PR no requiere cambios de esquema ni nueva migracion Alembic.

## 5) Ajustes de tests backend

### 5.1 Nuevo archivo de tests de autorizacion

Crear `backend/tests/test_owner_member_authorization.py` con cobertura minima:

1. Owner puede crear/editar products y locations.
2. Member no puede crear/editar products y locations (`403`).
3. Owner puede crear deliveries.
4. Member no puede crear deliveries (`403`).
5. Owner y member pueden listar/obtener resources (`GET` exitoso).
6. Usuario sin organizacion recibe `403` en endpoints que requieren organizacion.

### 5.2 Tests de organization members

Agregar casos:

1. Owner obtiene listado de miembros (`200`).
2. Member recibe `403` en `GET /organization-members`.
3. No autenticado recibe `401`.

### 5.3 Helpers de tests

Actualizar helpers compartidos para poder armar escenario owner/member en una misma organizacion sin invitaciones:

- crear owner con org via API
- crear segundo usuario y asociarlo a la organizacion del owner desde fixture/helper de test (solo contexto tests)

Objetivo: probar permisos reales sin adelantar feature de invitaciones.

## 6) Verificacion y checks del PR

Ejecutar:

1. `cd backend && uv run pytest -q`
2. Smoke manual minimo:
   - owner: POST/PATCH products y locations -> OK
   - member: POST/PATCH products y locations -> 403
   - owner: POST deliveries -> OK
   - member: POST deliveries -> 403
   - owner: GET /organization-members -> OK

## 7) Riesgos y mitigaciones

Riesgo: romper endpoints existentes al cambiar dependencias.
- Mitigacion: cubrir matriz completa owner/member en tests nuevos.

Riesgo: duplicar logica de permisos en routers.
- Mitigacion: centralizar chequeos en dependencias de `organizations/service.py`.

Riesgo: inconsistencia entre lectura y escritura.
- Mitigacion: definir regla explicita por endpoint (read owner/member, write owner).

## 8) Criterios de aceptacion del PR B

- Existe dependencia reutilizable para owner/member/user con organizacion.
- Endpoints de escritura (`products`, `locations`, `deliveries`) quedan restringidos a owner.
- Endpoints de lectura de esos modulos permiten owner y member.
- `GET /organization-members` existe y funciona solo para owner.
- No se introduce `users.role` nuevamente en ningun punto.
- Suite backend en verde.

## 9) Secuencia de implementacion sugerida (orden interno)

1. Implementar dependencias authz en `organizations/service.py`.
2. Exponer `GET /organization-members` + schemas.
3. Ajustar dependencias en routers de products/locations/deliveries.
4. Crear tests de autorizacion owner/member.
5. Ejecutar suite completa y smoke final.
