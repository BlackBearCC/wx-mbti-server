# Repository Guidelines

## Project Structure & Module Organization
The FastAPI app lives under `app/`, split into API routers (`app/api`), configuration and DB helpers (`app/config`), domain models (`app/models`), Pydantic schemas (`app/schemas`), and service layers (`app/services`). Reusable utilities sit in `app/utils`. Database migrations are driven by Alembic (`alembic.ini`, `app/models`, `migrations/`). Docker assets live in `docker/`, operational SQL in `scripts/`, and static files in `static/`.

## Build, Test, and Development Commands
Use `uvicorn app.main:app --reload` for a lightweight local server once a `.env` file mirrors `env.template`. `docker-compose up --build` spins up the full stack (PostgreSQL, Redis, API). Run `alembic upgrade head` after schema changes. Format code with `black app tests` and keep imports ordered via `isort app tests`. Type-check critical modules using `mypy app` before raising a PR.

## Coding Style & Naming Conventions
Stick to Black¡¯s default 88-character wrapping and four-space indentation. Modules and packages stay snake_case, classes are PascalCase, async functions use descriptive verbs (`sync_messages`, `issue_token`). Pydantic schema names should mirror their SQLAlchemy counterparts with `Schema` suffixes (e.g., `UserSchema`). Keep environment variables uppercase with prefixes (`APP_`, `DB_`).

## Testing Guidelines
Pytest is configured via `requirements.txt`; target meaningful coverage for `app/services` and `app/api`. Name files `test_<feature>.py` under `tests/`. For async endpoints leverage `pytest-asyncio` fixtures, and mock Redis/Postgres interactions where feasible. Run `pytest --cov=app tests/` before every push; include regression tests when fixing bugs in WebSocket or payment flows.

## Commit & Pull Request Guidelines
Follow imperative, present-tense commit titles (e.g., `Add room websocket heartbeat`). Reference issue IDs in the body when applicable. Each PR should describe scope, testing done, schema impacts, and rollback considerations; screenshots or curl samples help reviewers validate API deltas. Ensure lint, type checks, and pytest commands succeed locally before requesting review.

## Security & Configuration Tips
Never commit real credentials¡ªderive from `env.template`. JWT and Redis secrets must be rotated through your secrets manager. When adding new config knobs, document defaults in `README.md` and thread them through `pydantic-settings` so they can be overridden via environment variables or Docker Compose overrides.
