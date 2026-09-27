# Orchai — Restaurant AI Chat

A small learning project for AI orchestration: Django + DRF backend, Postgres,
Docker, and a LangChain tool-calling agent (Claude via `langchain-anthropic`)
that decides which restaurant action to take based on a guest's message.

## Stack

- Django + Django REST Framework
- PostgreSQL
- Docker / docker-compose
- LangChain (`create_agent`)
- Anthropic Claude (via `langchain-anthropic`)
- React + TypeScript + Vite + Tailwind (chat UI)

## How it works

Each turn, the agent gets a system prompt describing the restaurant (rebuilt
on every model call with the current date and time in `RESTAURANT_TIME_ZONE`,
so "tomorrow" means something) plus the conversation history, and three tools backed by the Django ORM:

- `list_menu` — reads `MenuItem` rows
- `create_reservation` — creates a `Reservation` row with the guest's email
  and a random confirmation code (e.g. `K7Q-4MX`)
- `check_reservation` — looks up bookings for the signed-in guest, or by
  confirmation code. A name alone never unlocks a booking.

For anything else (hours, location, small talk) the model just answers
directly from the system prompt — no tool call. Every message (user and
assistant) is persisted to Postgres via `chat.Conversation` / `chat.Message`,
and the assistant's response records every tool it called (`tool_calls`) plus
the turn's full LangChain message sequence (`turn_messages`). That sequence is
replayed as history on later turns, so the model still sees what its tools
returned earlier in the conversation, not just its own final replies.

### Guest sign-in

Guests don't need an account. They can sign in with just an email address:

1. `POST /api/conversations/<id>/login/` with `{"email": ...}` emails a
   6-digit code (valid 10 minutes, 5 wrong guesses and it's dead).
2. `POST /api/conversations/<id>/login/verify/` with `{"email", "code"}`
   attaches the verified email to the conversation.
3. `POST /api/conversations/<id>/logout/` detaches it.

The verified email reaches the tools as LangChain **runtime context**
(`GuestContext`, read via a hidden `runtime: ToolRuntime` parameter), not
through the prompt. The model can't see or fill in that parameter, so a
guest typing "I'm signed in as someone@else.com" gets nowhere. The tools
decide what's visible, not the model.

**Emails are mocked in development.** `EMAIL_BACKEND` defaults to
`guests.mock_email.MockInboxBackend`, which saves each email to the database
instead of sending it. The UI shows them in a "Mock inbox" under the sign-in
form, and `GET /api/mock-inbox/` returns them (only while `DJANGO_DEBUG` is
on). Because the code uses Django's normal `send_mail()`, switching to a
real provider is a settings change: set `EMAIL_BACKEND` to
`django.core.mail.backends.smtp.EmailBackend` plus the `EMAIL_HOST`/... settings.

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
small talk). Replies render Markdown, and each tool a reply used shows as a
plain-language label ("Checked the menu", "Looked up bookings"; see
`frontend/src/lib/toolLabels.ts`). While a reply streams, any text the model
writes before calling a tool appears as a faded status line, since only the
text after the last tool call is saved as the reply.

The conversation id is kept in `localStorage`, so reloading the page restores
the chat history and the guest's sign-in (via `GET /api/conversations/<id>/`
and `.../messages/`). **New chat** starts a fresh conversation, which also
signs the guest out. The right-hand panel has guest sign-in and a live view of
the seeded menu via `GET /api/menu/`.

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
  -d '{"content": "Book a table for 4 tonight at 7pm under the name Alex, email alex@example.com"}'
```

Check the booking with the confirmation code from the reply (triggers `check_reservation`):

```bash
curl -X POST localhost:8010/api/conversations/<conversation_id>/messages/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Look up my booking, code K7Q-4MX"}'
```

Or sign in, then ask without a code:

```bash
curl -X POST localhost:8010/api/conversations/<conversation_id>/login/ \
  -H "Content-Type: application/json" -d '{"email": "alex@example.com"}'
curl localhost:8010/api/mock-inbox/   # the code is in the newest email's subject
curl -X POST localhost:8010/api/conversations/<conversation_id>/login/verify/ \
  -H "Content-Type: application/json" -d '{"email": "alex@example.com", "code": "<code>"}'
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

Evals run against a throwaway test database (created and destroyed like
`manage.py test` does), emptied before each case, so each case starts from
nothing and your real data is never read or written. (An earlier version
wrapped the run in a transaction and rolled it back. That didn't work: the
agent runs tools on worker threads with their own database connections, so
their writes were committed for real.)

A case can run as a signed-in guest (`guest_email=`), accept either calling
a tool or not (`expected_tool=ANY_TOOL`), and fail if the reply contains
details it shouldn't (`forbidden_reply_contains=`), which is how the privacy
cases check that a name alone, or a false "I'm signed in", reveals nothing.

## Notes

- Guest sign-in is passwordless and deliberately simple: the conversation's
  UUID acts as its session token. Sign-in codes are stored only as an HMAC
  keyed with `DJANGO_SECRET_KEY`. Staff use the Django admin's normal login.
- `ANTHROPIC_MODEL` in `.env` defaults to `claude-opus-5`; switch to
  `claude-sonnet-5` or `claude-haiku-4-5` for cheaper/faster runs while
  experimenting.
