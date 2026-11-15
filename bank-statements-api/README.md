# Bank Statement Analyzer API

Backend API for the Bank Statement Analyzer: parses uploaded bank statements,
categorises transactions, and serves them over a REST API.

Structure, schema and data flow live in [ARCHITECTURE.md](../ARCHITECTURE.md), and the
code is the authority on both. This file covers only what you cannot read off the code:
how to run the thing, and why it is shaped the way it is.

## Running it

From the repository root, not from here:

```
pnpm install:api     # uv sync
pnpm db:start        # postgres in docker, then alembic upgrade head
pnpm dev:api         # http://localhost:8000
```

`pnpm start` runs the API and the web app together. For the local auth bypass and
running as a specific user, see "Local Auth Bypass" in [CLAUDE.md](../CLAUDE.md).

Interactive API docs once it is up: `/docs` (Swagger) or `/redoc`.

## Tests

```
pnpm test:api              # unit + integration
pnpm check:api             # isort, black, ruff
```

Integration tests need the test database (`pnpm test:db:up`) and build their schema by
running the migrations, never `create_all`, so they stay on the same schema as production.

There is also a black-box behavioural suite that drives the running API over HTTP:
`tests/behavioural/bin/bsai-api-verify`. See `tests/behavioural/README.md`.

## Why it is shaped this way

**Hexagonal architecture.** Interfaces in `app/ports/`, implementations in
`app/adapters/`. Services depend on the port, so the database can be swapped in tests
without touching business logic.

**The models are the source of truth for the schema.** Migrations are derived from them
with `alembic revision --autogenerate`, never hand-written for schema operations, and
`alembic check` must report nothing pending. CI enforces it.

**Accounts and counterparties are separate tables, deliberately.** An account is yours:
it has a currency and owns statements, initial balances and import configs. A
counterparty is someone you transact with. They were one table once, which meant a
statement could attach to your landlord. A transaction's other side is therefore either
`counterparty_id` or `transfer_account_id`, never both, enforced by a check constraint
rather than by convention.

**Multi-tenancy is enforced in the repositories.** Every query filters by `user_id`. A
foreign key proves a row exists, not that it belongs to the caller, so services validate
ownership separately.
