# Repository Guidelines

## Project Structure & Module Organization
The FastAPI app lives under `app/`, split into API routers (`app/api`), configuration and DB helpers (`app/config`), domain models (`app/models`), Pydantic schemas (`app/schemas`), and service layers (`app/services`). Reusable utilities sit in `app/utils`. Database migrations are driven by Alembic (`alembic.ini`, `app/models`, `migrations/`). Docker assets live in `docker/`, operational SQL in `scripts/`, and static files in `static/`.

## Build, Test, and Development Commands
Use `uvicorn app.main:app --reload` for a local server once `.env` mirrors `env.template`. `docker-compose up --build` spins up the full stack. Run `alembic upgrade head` after schema changes. Format with `black app tests` and `isort app tests`. Type-check critical modules using `mypy app` before a PR.

## Coding Style & Naming Conventions
Black default line length (88) and four-space indentation. Modules/packages are snake_case, classes are PascalCase, async function names are descriptive (e.g., `sync_messages`, `issue_token`). Pydantic schema names mirror SQLAlchemy models with `Schema` suffix (e.g., `UserSchema`). Environment variables are UPPERCASE with prefixes (`APP_`, `DB_`).

## Testing Guidelines
Pytest configured via `requirements.txt`. Focus on `app/services` and `app/api`. Name files `test_<feature>.py` under `tests/`. For async endpoints use `pytest-asyncio` and mock Redis/Postgres when possible. Run `pytest --cov=app tests/` before every push; include regression tests for WebSocket or payment flows.

## Commit & Pull Request Guidelines
Use imperative, present-tense commit titles (e.g., `Add room websocket heartbeat`). Reference issue IDs when applicable. Each PR describes scope, testing, schema impacts, and rollback considerations; screenshots or curl samples help reviewers validate API changes. Ensure lint, type checks, and tests succeed locally before review.

## Security & Configuration Tips
Never commit real credentials; derive from `env.template`. JWT and Redis secrets must be rotated via your secrets manager. When adding new config knobs, document defaults in `README.md` and wire them through `pydantic-settings` so they are overridable via env or Compose overrides.

## External LLM Interface (HTTPS/WSS Gateway Only)

- Transport: Only HTTPS/WSS. Always serve and reference assets over `https://` and connect WebSocket via `wss://`.
- Do not expose `provider` to clients. Clients pass only `modelAlias`; the server maps alias -> provider+model via env config. The old internal endpoint `POST /api/chat/send` has been removed.

- HTTP (non-stream over HTTPS): `POST /service/chat`
  - Request
    - `messages`: array of `{role: system|user|assistant, content: string}`
    - `modelAlias`: string (optional; defaults to `AI_DEFAULT_MODEL_ALIAS` if set)
    - `temperature`: float (optional)
    - `maxTokens`: int (optional)
    - `metadata`: object (optional)
  - Response
    - `{ code: 200, data: { text, model, usage, created } }`

- HTTP (stream, SSE over HTTPS): `POST /service/streamchat`
  - Response media type: `text/event-stream`
  - Server emits `data: <chunk>` lines and terminates with `data: [DONE]`

- WebSocket Gateway (WSS): `/service/ws`
  - Envelope (client -> server)
    ```json
    { "reqId": "r-123", "op": "ai.chat" | "ai.stream" | "ping" | "room.join" | "room.leave" | "room.typing", "data": { ... } }
    ```
  - ai.chat data
    - `messages`, `modelAlias`, optional `temperature`, `maxTokens`, `metadata`, `characterName`, `systemPrompt`, and optional `userId/roomId/characterId`.
  - ai.chat response
    - `{ "reqId": "r-123", "op": "ai.chat", "event": "result", "text": "...", "model": "...", "usage": { ... } }`
  - ai.stream responses
    - `start` -> many `chunk` -> `final` -> `done` (all frames include `reqId` and `op`)
  - room ops (minimal demo)
    - `room.join` / `room.leave` -> `{event: "result"}`
    - `room.typing` -> broadcast `{op: "room.typing", event: "update", roomId, userId}` to room peers and `ack` to sender

### Local TLS For Development

- Windows (mkcert):
  - Install: `choco install mkcert` (once), then `mkcert -install`
  - Generate local certs: `mkcert localhost 127.0.0.1`
    - Produces files like `localhost+2.pem` and `localhost+2-key.pem`
  - Start Uvicorn with TLS:
    - `uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-certfile .\localhost+2.pem --ssl-keyfile .\localhost+2-key.pem`
- Docker Compose:
  - Place the certs under project `./.cert/` and compose will mount to `/app/certs` by default.
  - The container entrypoint auto-detects `/app/certs/*-key.pem` and `*.pem` and starts Uvicorn with `--ssl-*`.
  - Healthcheck uses `curl -kf https://localhost:8000/health`.
- WeChat DevTools:
  - Add only HTTPS/WSS domain(s).
  - For self-signed cert during local dev, enable the option to skip certificate checks if needed (dev only).

### Alias and Provider Configuration
- `AI_MODEL_ALIASES` (JSON) defines alias mapping, e.g.
  ```json
  { "default": {"provider": "doubao", "model": "ep-20240901-chatglm-3-6b", "max_tokens": 1024, "temperature": 0.7},
    "gpt4o-mini": {"provider": "openai", "model": "gpt-4o-mini"} }
  ```
- `AI_PROVIDER_OVERRIDES` (JSON) can set vendor `api_key`, `base_url`, `timeout`, and nested `aliases`.
- `AI_DEFAULT_MODEL_ALIAS` selects the default alias when clients omit `modelAlias`.
- `AI_STREAM_ENABLED` gates streaming endpoints.

### Auth and Rate Limit
- HTTP endpoints under `/service/*` require token auth:
  - Header: `Authorization: Bearer <token>` or `X-API-Key: <token>`
  - Configure allowed tokens via env `API_TOKENS` (comma-separated or JSON array). For local dev, `dev-token` is accepted if `API_TOKENS` is unset.
- WebSocket gateway `/service/ws` requires token:
  - Pass as query `?token=<token>`, or after connect send `{op:"auth", data:{token:"..."}}`.
  - `ping` is allowed pre-auth; `ai.*`/`room.*` require auth.
- Rate limiting (fixed window via Redis, with in-process fallback):
  - Config: `RATE_LIMIT_REQUESTS` per `RATE_LIMIT_WINDOW` seconds.
  - Applied to: `POST /service/chat`, `POST /service/streamchat`, `ws ai.chat`, `ws ai.stream`.
