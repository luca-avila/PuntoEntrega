# Step-by-Step Build Plan for `steps.md` (MVP Multi-Tenant SaaS)

## Summary
- Build a multi-tenant MVP for delivery/consignation registration, reusing existing auth.
- Keep modular monolith boundaries and thin API handlers.
- Locked choices:
  - Organization assignment: auto-create organization on user registration.
  - Map: Leaflet + OpenStreetMap.
  - Delivery email recipients: global environment-configured list.
  - Language rule: codebase can be in English, but all user-facing content must be Spanish (UI, emails, and user-visible errors).

## Implementation Steps
1. **Project baseline**
   - Create `steps.md` with this plan.
   - Keep current stack/conventions from `AGENTS.md`.
   - Define feature modules: `organizations`, `locations`, `products`, `deliveries`, `mail`.

2. **Data model + migrations**
   - Add `Organization` model (`id`, `name`, `slug`, timestamps, optional subscription placeholders).
   - Extend `User` with `organization_id` (and optional `role`).
   - Add `Location`, `Product`, `Delivery`, `DeliveryItem`.
   - Add enums:
     - `payment_method`: `cash`, `transfer`, `current_account`, `other`
     - `email_status`: `pending`, `sent`, `failed`
   - Create deterministic Alembic migrations.

3. **Auth integration + tenant scoping**
   - Reuse existing auth module.
   - On registration, create organization + user atomically.
   - Expose organization info via current-user endpoint.
   - Add shared organization-scoping helpers and ownership checks.

4. **Locations feature**
   - Implement `GET/POST /locations`, `GET/PATCH /locations/{id}`.
   - Persist `address`, `latitude`, `longitude`.
   - Enforce strict organization isolation on all operations.

5. **Products feature**
   - Implement `GET/POST /products`, `GET/PATCH /products/{id}`.
   - Organization-scoped catalog with `is_active`.
   - Exclude inactive products from new delivery form options.

6. **Deliveries feature (core flow)**
   - Implement `GET/POST /deliveries`, `GET /deliveries/{id}`.
   - Validate: required location/delivered_at/payment_method, at least one item, quantity > 0, same-organization ownership.
   - Save delivery + items in one DB transaction.
   - Add history filters by location/date.

7. **Email workflow**
   - Add setting `DELIVERY_SUMMARY_RECIPIENTS`.
   - After successful DB commit, send summary email.
   - If email fails, keep delivery and set `email_status=failed` (no rollback).

8. **Spanish-first user experience**
   - Frontend text in Spanish.
   - Delivery summary email templates in Spanish.
   - User-visible backend validation/business errors in Spanish.
   - Keep internal enum values and code identifiers in English.

9. **Frontend bootstrap**
   - Initialize React + TypeScript + Vite + Tailwind + React Hook Form + shadcn/ui.
   - Keep structure simple: `src/pages`, `src/components`, `src/api`, `src/hooks`.
   - Implement cookie-auth API client and protected routing.

10. **Frontend screens**
   - Login (existing auth).
   - Locations list + create/edit with embedded Leaflet map picker (no raw lat/lng inputs).
   - Products list + create/edit.
   - New delivery form with multiple item rows and payment fields.
   - Delivery history and delivery detail with email status visibility.

11. **Validation, UX, and reliability**
   - Add loading/empty/error states.
   - Keep mobile-friendly operational UX.
   - Avoid unnecessary frontend abstraction.

12. **Completion and documentation**
   - Update `.env.example` and README for new variables and run steps.
   - Validate full Definition of Done from `plan.md`.
   - Confirm excluded scope is not implemented.

## Public API / Interface Changes
- New entities: `organizations`, `locations`, `products`, `deliveries`, `delivery_items`.
- User payload includes `organization_id` (optional `role`).
- New endpoints:
  - `GET/POST /locations`, `GET/PATCH /locations/{id}`
  - `GET/POST /products`, `GET/PATCH /products/{id}`
  - `GET/POST /deliveries`, `GET /deliveries/{id}`
- New env variable:
  - `DELIVERY_SUMMARY_RECIPIENTS`

## Test Scenarios
1. Registration auto-creates and links organization.
2. Org A cannot read/update Org B records.
3. Delivery validation rejects missing fields, empty items, and non-positive quantities.
4. Delivery creation rejects cross-organization location/product references.
5. Email success sets `email_status=sent`.
6. Email failure keeps persisted delivery and sets `email_status=failed`.
7. Location form stores coordinates through map interaction, not manual lat/lng entry.
8. UI, emails, and user-visible errors are Spanish.

## Assumptions
- MVP supports one organization per user.
- Email recipients are global (env-based) in MVP.
- No real subscription/payment gateway in this phase.
- No delivery edit flow unless explicitly requested later.
