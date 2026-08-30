# Orchai — Restaurant AI Chat

A small learning project for AI orchestration: Django + DRF backend, Postgres,
Docker, and a LangChain tool-calling agent (Claude via `langchain-anthropic`)
that decides which restaurant action to take based on a guest's message.

## Stack

- Django + Django REST Framework
- PostgreSQL
- Docker / docker-compose
- LangChain (`create_tool_calling_agent` + `AgentExecutor`)
- Anthropic Claude (via `langchain-anthropic`)
- React + TypeScript + Vite + Tailwind (chat UI)

## How it works

Each turn, the agent gets a system prompt describing the restaurant plus the
conversation history, and three tools backed by the Django ORM:

- `list_menu` — reads `MenuItem` rows
- `create_reservation` — creates a `Reservation` row
- `check_reservation` — looks up `Reservation` rows by customer name

For anything else (hours, location, small talk) the model just answers
directly from the system prompt — no tool call. Every message (user and
assistant) is persisted to Postgres via `chat.Conversation` / `chat.Message`,
and the assistant's response records which tool (if any) it used.

## Setup

1. Copy the env file and add your Anthropic API key:

   ```bash
   cp .env.example .env
   # edit .env and set ANTHROPIC_API_KEY
   ```

2. Build and start everything (Postgres, the Django API, and the React UI):

   ```bash
   docker compose up --build
   ```

3. In another terminal, run migrations and seed the sample menu:

   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py seed_menu
   ```

## UI

Open [localhost:5173](http://localhost:5173). A conversation starts
automatically; the chat panel covers all four backend behaviors depending on
what you type (menu question, booking request, booking lookup, or general
small talk), and shows a `🔧 tool_name` badge on any assistant reply that
triggered a tool call. The right-hand panel is a live view of the seeded menu
via `GET /api/menu/`.

If `ANTHROPIC_API_KEY` in `.env` is still the placeholder value, sending a
message will show a visible error bubble instead of a reply — that's expected
and confirms the request reached the agent.

The frontend runs via Vite's dev server with hot reload (`frontend/` bind-mounted
into the `frontend` container), so edits to `frontend/src` show up immediately.

## Try it (raw API)

Create a conversation:

```bash
curl -X POST localhost:8010/api/conversations/
# => {"id": "<conversation_id>", "created_at": "..."}
```

Ask about the menu (triggers `list_menu`):

```bash
curl -X POST localhost:8010/api/conversations/<conversation_id>/messages/ \
  -H "Content-Type: application/json" \
  -d '{"content": "What'\''s on the menu?"}'
```

Book a table (triggers `create_reservation`):

```bash
curl -X POST localhost:8010/api/conversations/<conversation_id>/messages/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Book a table for 4 tonight at 7pm under the name Alex"}'
```

Check the booking (triggers `check_reservation`):

```bash
curl -X POST localhost:8010/api/conversations/<conversation_id>/messages/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Do you have a table booked for Alex?"}'
```

Ask a general question (no tool call):

```bash
curl -X POST localhost:8010/api/conversations/<conversation_id>/messages/ \
  -H "Content-Type: application/json" \
  -d '{"content": "What time do you close?"}'
```

View full history:

```bash
curl localhost:8010/api/conversations/<conversation_id>/messages/
```

Browse the seeded menu directly:

```bash
curl localhost:8010/api/menu/
```

## Testing & evals

Two separate layers, on purpose — they check different things and have very
different cost/speed profiles:

**Unit tests** (`chat/tests/`) — free, fast, deterministic. Cover the tool
functions (`list_menu`, `create_reservation`, `check_reservation`) against a
real test database, the API views (with the agent mocked out), and the
orchestrator glue code (history conversion, result unpacking). Run:

```bash
docker compose exec web python manage.py test
```

**Evals** (`chat/agent/eval_cases.py`, run via `manage.py run_evals`) — make
real, billed calls to the Claude API through the actual agent, so they check
judgment: did it pick the right tool for the message, extract the right
arguments, and answer directly when no tool was needed. They do not run as
part of `manage.py test` and are not part of CI — run them manually after
changing the system prompt, tools, or model:

```bash
docker compose exec web python manage.py run_evals
docker compose exec web python manage.py run_evals --case create_reservation_extracts_all_fields
```

Any DB rows a case's setup creates (seeded menu items, a seeded reservation)
are rolled back at the end of the run via an outer transaction, so this is
safe to run against a real database — nothing an eval creates persists. Note
that eval cases run inside that same transaction as whatever's already in
the database, so pre-existing rows (e.g. from manual testing) are visible to
the model during a run even though the eval's own writes don't stick around.

## Notes

- No authentication — this is a local learning demo.
- `ANTHROPIC_MODEL` in `.env` defaults to `claude-opus-5`; switch to
  `claude-sonnet-5` or `claude-haiku-4-5` for cheaper/faster runs while
  experimenting.
