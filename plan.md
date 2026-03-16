Build an MVP for a generic SaaS web app used by small businesses to register product deliveries / consignations to physical business locations such as restaurants, dietéticas, and similar stores.

This is not a one-off internal app for a single client.
It must be designed as a multi-tenant SaaS, where each customer account has isolated data.

Use the existing stack, patterns, and project conventions already defined in agents.md.

Reuse the existing authentication module already available in the codebase.
Do not build authentication from scratch.

Core product goal

Each customer organization should be able to:

manage its own business locations

manage its own product catalog

register deliveries / consignations to those locations

store payment information for each delivery

store map-based location data for each location

review delivery history

send delivery summaries by email to logistics and billing contacts

The product should be generic enough to be reused across multiple small businesses, not just one specific mushroom seller.

Critical architecture requirement: multi-tenant SaaS

Design the app as organization-scoped from day one.

There must be a concept such as:

organization

workspace

account

Use one clear term consistently; prefer Organization.

Each authenticated user must belong to an organization.

Operational data must be isolated per organization.

At minimum, the following entities must be organization-scoped:

locations

products

deliveries

That means:

one organization must never see another organization’s data

all reads/writes must be scoped to the current authenticated user’s organization

Do not fake SaaS by only adding is_paid to the user model.

The important concept is organization ownership and data isolation, not just paid/unpaid users.

Billing / subscription boundary

Do not implement real payment provider integration in this MVP yet.

However, the architecture should be ready for future subscription support.

Prepare the data model so that subscription status can later be attached to the organization.

That means future-ready support for concepts like:

plan

subscription status

active/inactive organization access

But for now, keep billing implementation minimal or absent unless explicitly needed for scaffolding.

If you need a placeholder model, use an organization-level billing/subscription concept, not a user-level is_paid flag as the core design.

Explicitly out of scope

Do not implement any of the following in this MVP:

payment gateway integration

Mercado Pago integration

real subscription checkout flow

signature capture

invoice/remito/legal document generation

stock shortage notifications

replenishment workflows

route optimization

offline support

advanced analytics dashboards

full admin/operator panel separation

complex RBAC

You may leave extension points for future features, but do not build them now.

Existing auth requirement

Reuse the existing auth module.

Extend it only as needed to support organization-aware access.

Likely needs:

user belongs to organization

optional future role field if useful

Do not redesign auth unnecessarily.

Main MVP workflow

The central workflow is registering a delivery.

Flow:

User authenticates through the existing auth module.

User belongs to one organization.

User creates or selects one of their organization’s locations.

User creates or selects one of their organization’s products.

User opens the new delivery form.

User selects a location.

User adds one or more products with quantities.

User selects a payment method.

User optionally adds payment notes and observations.

User submits the delivery.

Backend stores the delivery and its items.

Backend sends a summary email to configured recipients.

UI shows success/error state and email status.

Keep the app focused on this operational flow.

Domain model requirements

Implement at least these entities.

Organization

Represents a customer account / tenant.

Fields should include at least:

id

name

slug or identifier if useful

created_at

updated_at

Optionally leave room for:

subscription_status

plan_code

is_active

But do not overbuild billing now.

User

Reuse the existing auth user model.

Extend it minimally to support organization membership.

At minimum, user should be associated with an organization.

If useful, add a simple role field for future evolution, but do not implement advanced role logic in MVP.

Location

Represents a physical business location belonging to an organization.

Fields:

id

organization_id

name

address

contact_name

contact_phone

contact_email

latitude

longitude

notes

created_at

updated_at

Product

Represents a product belonging to an organization.

Fields:

id

organization_id

name

description

is_active

created_at

updated_at

Delivery

Represents one delivery / consignation event belonging to an organization.

Fields:

id

organization_id

location_id

delivered_at

payment_method

payment_notes

observations

email_status

created_at

updated_at

DeliveryItem

Represents one line item inside a delivery.

Fields:

id

delivery_id

product_id

quantity

Keep the model simple and clean.

Location UX requirement

Do not expose manual latitude/longitude text inputs to the user.

The location form must support:

manual address entry

embedded interactive map

visual selection or adjustment of a point

persistence of the resulting coordinates behind the scenes

Expected UX:

user types or edits the address

user sees an embedded map

user selects or adjusts the point visually

frontend stores derived latitude and longitude

backend persists address + lat/lng

Coordinates are persisted data, but not direct user-entered fields.

Do not hardcode the product requirement to Google Maps specifically.
Use a map-based solution that fits the project and scope, but the UX must be embedded and interactive.

Also, a location may exist in the system even if it is not a public Google Maps place.

Product requirements

Each organization has its own product catalog.

Each product supports:

name

optional description

active/inactive status

Only the current organization’s products should appear in its delivery forms.

Inactive products should not appear in new delivery creation unless there is a clear reason.

Delivery requirements

Each delivery belongs to one organization and one location.

Each delivery supports:

location

delivered_at datetime

payment_method

payment_notes

observations

email_status

Each delivery must contain one or more delivery items.

Each delivery item supports:

product

quantity

Validation:

location required

delivered_at required

payment_method required

at least one item required

each quantity must be > 0

all referenced data must belong to the current organization

This last point is critical:

users must not be able to attach another organization’s location or products to their delivery

Payment requirements

For MVP, store payment info as simple structured data on the delivery.

At minimum:

payment_method

optional payment_notes

Keep payment method simple.
A fixed enum or controlled set is enough, for example:

cash

transfer

current_account

other

Do not implement financial accounting logic.

Delivery history requirements

Build a delivery history view scoped to the current organization.

At minimum show:

delivery date/time

location name

payment method

email status

items summary

If simple enough, include filters:

by location

by date

Also implement a delivery detail view.

Email workflow requirements

After a delivery is successfully created, send a summary email.

Use configurable recipients from environment/settings for MVP.

Recipients may later become organization-specific, but do not overcomplicate that now unless needed.

Email content should include:

delivery date/time

organization name if useful

location name

address

contact data

delivered products with quantities

payment method

payment notes

observations

Important backend rule

Persistence is primary. Email is secondary.

If DB save succeeds but email sending fails:

keep the delivery saved

mark email_status = failed

expose that status clearly

Do not roll back a valid delivery record because of email failure unless there is a very strong reason.

Pages / screens

Build the minimal set of screens needed for a usable SaaS MVP.

login page using existing auth

locations list page

location create/edit page

products list page

product create/edit page

new delivery page

delivery history page

delivery detail page

Optionally include a lightweight dashboard/home page if useful, but do not let it expand scope.

Prioritize practical mobile-friendly UX over visual polish.

Backend behavior expectations

Follow the existing project conventions and architecture from agents.md.

Use feature-oriented organization.

Suggested structure:

organization-aware auth/access helpers

locations feature

products feature

deliveries feature

mail/email service

Keep logic clean and practical:

schemas

models

repositories if useful

services / use cases

routes

Do not over-abstract.

Organization scoping rules

This is critical.

All queries and mutations for organization-owned data must be scoped to the current user’s organization.

Examples:

list locations => only current org locations

create product => automatically tied to current org

create delivery => current org only

retrieve delivery detail => only if it belongs to current org

Never trust raw foreign keys from the client without checking organization ownership.

Suggested API surface

Implement a clean MVP API.

Organizations

You may keep organization APIs minimal if signup/onboarding is not yet in scope.

Locations

GET /locations

POST /locations

GET /locations/{id}

PATCH /locations/{id}

Products

GET /products

POST /products

GET /products/{id}

PATCH /products/{id}

Deliveries

GET /deliveries

POST /deliveries

GET /deliveries/{id}

Optional later:

PATCH /deliveries/{id} only if clearly needed

Frontend expectations

Frontend must:

be responsive and mobile-friendly

be simple and fast

support multiple delivery item rows

hide coordinate complexity behind the map UI

show email status clearly

feel like an operational tool, not a marketing site

Do not overcomplicate design.

Technical guidance

Use the stack already defined in agents.md.

Additional guidance:

keep the app simple and production-usable

keep the delivery flow central

support multi-tenancy cleanly from the start

do not prematurely build billing or stock systems

keep future extension possible without speculative complexity

Recommended implementation order

extend/reuse existing auth to support organization membership

add organization model and current-organization scoping

implement location model + CRUD scoped to organization

implement product model + CRUD scoped to organization

implement delivery + delivery items scoped to organization

implement create-delivery use case with validation

implement email sending + email status

implement location UI with address + embedded map picker

implement products UI

implement new delivery UI

implement delivery history/detail UI

polish validation, loading states, and error handling

Definition of done

The MVP is done when:

existing auth is reused successfully

each user belongs to an organization

organization-scoped data isolation works

locations can be created and edited

location form uses address + embedded map selection

users do not manually type raw lat/lng

products can be managed per organization

deliveries can be created with multiple items

payment info is stored

delivery history is visible per organization

delivery detail is visible per organization

email is sent after delivery creation

failed email attempts do not delete valid delivery data

the app works as a small mobile-friendly SaaS MVP

excluded features were not implemented