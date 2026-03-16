# AI Agent Operating Rules

## Core Objective

Generate production-minded, maintainable code.

Prioritize:

1. correctness
2. clarity
3. explicit structure
4. long-term maintainability

Do NOT optimize for cleverness.
Do NOT optimize for novelty.
Do NOT introduce unnecessary complexity.

---

## Default Architecture

Unless explicitly instructed otherwise:

- Use a modular monolith.
- Keep clear feature/module boundaries.
- Avoid microservices.
- Avoid distributed complexity.
- Avoid premature abstraction.

Prefer feature-first organization over technical-layer sprawl.

---

## Separation of Responsibilities

Keep responsibilities clearly separated:

- Business/domain logic
- Application/use-case orchestration
- Infrastructure/persistence
- Interface/transport layer (HTTP, CLI, jobs, etc.)

Rules:

- Do NOT put business logic inside controllers/routers/handlers.
- Do NOT put business logic inside ORM models unless the project is intentionally trivial.
- Do NOT let infrastructure dictate business structure.
- Handlers must remain thin.

---

## Business Logic Rules

Business rules must be:

- explicit
- easy to locate
- enforced in one clear place

If a rule affects correctness, it must live in domain or application logic — not scattered across helpers.

Avoid:

- “god services”
- giant utility modules
- hidden side effects
- implicit behavior

Prefer:

- small focused functions
- explicit state transitions
- obvious invariants

---

## Persistence Rules

- Respect the existing persistence approach.
- Use the project’s current ORM/migration system.
- Do NOT introduce raw SQL unless explicitly required.
- Do NOT redesign persistence patterns unless requested.

Database models are persistence models.
They are not automatically the domain model.

---

## Transaction and Consistency Rules

For state-changing operations:

- keep changes atomic
- respect transaction boundaries
- prevent race conditions when relevant
- never split critical updates across unsafe steps

Correctness > cleverness.

---

## Existing Stack Respect

Always respect:

- the existing framework
- the existing dependency manager
- the current project structure
- established conventions

Do NOT:

- replace tools without explicit instruction
- introduce new dependency managers
- add trendy libraries without a clear need
- redesign the whole architecture casually

Extend the current system. Do not fight it.

---

## Dependency Rules

- Minimize new dependencies.
- Prefer standard library or existing dependencies.
- Every new dependency must have clear value.

No novelty-driven additions.

---

## Refactoring Rules

When modifying code:

- preserve working behavior
- avoid unrelated refactors
- avoid renaming everything
- avoid structural churn

Only change what is necessary.

---

## Naming Rules

Use names that are:

- explicit
- descriptive
- stable
- business-aligned

Avoid vague names like:
- manager
- helper
- utils
- process_data
- handle_stuff

Names must communicate intent.

---

## API / Handler Rules

If the project exposes an API:

- Keep handlers thin.
- Validate input.
- Call a use case or service.
- Return structured output.
- Translate internal errors cleanly.

Do NOT:

- place transaction logic in handlers
- place business calculations in handlers
- place heavy persistence logic in handlers

---

## Performance Mindset

Do not prematurely optimize.

Default order of priorities:

1. correctness
2. clarity
3. maintainability
4. performance (when needed)

However:

- avoid obviously inefficient patterns
- avoid unnecessary repeated work
- be mindful of N+1 patterns in data access

---

## Security Rules

- Respect existing authentication/authorization boundaries.
- Do NOT bypass auth.
- Do NOT duplicate auth logic.
- Never hardcode secrets.
- Validate external input carefully.

---

## What NOT to Do

- Do not introduce microservices by default.
- Do not over-abstract early.
- Do not mix layers irresponsibly.
- Do not tightly couple business logic to infrastructure.
- Do not create giant shared “utils” dumping grounds.
- Do not redesign architecture without being asked.
- Do not choose cleverness over clarity.

---

## Implementation Order Rule

When adding a feature:

1. understand the goal
2. define the behavior and rules
3. implement the core logic
4. integrate persistence
5. expose through interface
6. align with existing conventions

Start from behavior, not from the database schema alone.

---

## Frontend Rules

Frontend exists to support the backend and product workflow.

The frontend should remain simple and avoid unnecessary architectural complexity.

Priorities:

1. speed of development
2. clarity
3. maintainability
4. minimal frontend complexity

Avoid frontend over-engineering.

---

### Default Frontend Stack

Unless explicitly instructed otherwise, use:

- React
- TypeScript
- Vite
- TailwindCSS
- React Hook Form (for forms)
- shadcn/ui (for UI components)

Do NOT introduce additional frameworks or heavy UI systems unless required.

Avoid:

- Redux
- complex state management libraries
- CSS frameworks that conflict with Tailwind
- unnecessary UI libraries
- experimental frontend architectures

---

### Frontend Responsibility

The frontend is responsible for:

- rendering UI
- collecting user input
- calling backend APIs
- displaying backend data

Business rules and critical logic must remain in the backend.

Do not duplicate backend logic in the frontend.

---

### State Management Rules

Prefer simple patterns:

- local component state
- minimal lifting of state
- backend-driven state when possible

Avoid global state unless clearly required.

Do not introduce complex state management systems prematurely.

---

### Form Handling

Forms should use **React Hook Form**.

Rules:

- keep form logic simple
- validate inputs when necessary
- submit data to backend endpoints
- avoid unnecessary abstraction layers

---

### Styling Rules

Use **TailwindCSS** for styling.

Avoid:

- large custom CSS files
- complex styling systems
- unnecessary design abstraction

Favor simple utility-based styling.

---

### UI Components

Prefer **shadcn/ui** components for common UI elements such as:

- buttons
- inputs
- dialogs
- tables
- basic layout components

Do not create large custom design systems unless required.

Reuse existing components whenever possible.

---

### Frontend Structure

Keep the frontend structure simple:
src/
pages/
components/
api/
hooks/


Definitions:

- pages → application screens
- components → reusable UI components
- api → backend request helpers
- hooks → small reusable logic

Avoid unnecessary architectural layers.

---

### Data Flow

Frontend should interact with the backend through simple API calls.

Typical flow:

React UI → API request → Backend → Database

Keep the frontend thin and backend-driven whenever possible.

---

### Complexity Rule

If frontend complexity increases:

- move logic to the backend when possible
- simplify UI behavior
- avoid introducing additional frameworks

Prefer backend-driven solutions over frontend complexity.

---

## Final Directive

Write code that:

- a developer can understand in 6 months
- is easy to modify
- has clear boundaries
- does not surprise its reader

Clarity over cleverness.
Structure over chaos.
Stability over novelty.

## Backend Stack

Unless explicitly instructed otherwise, backend services should use:

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic for migrations
- uv as dependency manager
- Docker for containerization

Do NOT introduce alternative frameworks or infrastructure without explicit instruction.

Avoid introducing:

- new ORMs
- alternative migration systems
- unnecessary background job systems
- complex infrastructure tooling

Prefer simple, explicit backend architecture aligned with the modular monolith approach.

---

### Backend Structure

Follow a feature-first structure when possible.

Example:

backend/
  features/
    auth/
    products/
    orders/
  core/
    config
    db
    logging
  main.py

Rules:

- features contain domain + application logic
- core contains shared infrastructure
- routers must remain thin
- business logic must live inside feature modules

---

### Migrations

Database schema changes must use **Alembic migrations**.

Rules:

- never modify schema manually in production
- always generate a migration
- migrations must be versioned
- migrations must remain deterministic

---

### API Layer

Use FastAPI routers.

Rules:

- routers must remain thin
- routers validate input
- routers call use cases/services
- routers return structured responses

Business logic must never live in routers.
