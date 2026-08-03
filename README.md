# S32 Sourcing

Multi-partner sourcing and signal-tracking pipeline for S32 (~5–15 partners).

One shared data pipeline and Affinity push. Each partner owns thesis areas, a watchlist, and a rubric overlay on the firm-wide base rubric.

## Architecture

```
Specter / Exa / GitHub ──► normalize + dedupe ──► Clay enrich
                              │
                              ▼
                     base score (once) + why-note
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         Team Queue     My Queue (overlay)  Affinity push
```

| Resource | Scope |
|---|---|
| companies, people, signals, scores | Firm-wide |
| thesis_configs | Per partner or shared (`partner_id` null) |
| watchlist_entries, rubric_overlays | Per partner |
| feedback | Per-partner write; visible to all |
| rubric_base | Firm-wide; admin write |

## Quick start (local)

```bash
cp .env.example .env
# Fill EXA_API_KEY, GITHUB_TOKEN, ANTHROPIC_API_KEY at minimum
# For local UI without Clerk: AUTH_DEV_BYPASS=true

# Option A — Docker (API + DB + worker + frontend)
docker compose up --build

# Option B — native
# start Postgres (docker compose up -d db  OR  brew services start postgresql@16)
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_demo.py
uvicorn app.main:app --reload --port 8000

cd ../frontend
cp .env.local.example .env.local
npm install && npm run dev
```

- App: http://localhost:3000  
- API docs: http://localhost:8000/docs  

## Team / production setup

1. **Clerk** — create an application, invite partners (Google OAuth recommended). Set `CLERK_SECRET_KEY` + `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`. Set `AUTH_DEV_BYPASS=false`.
2. **Postgres** — managed (Neon/RDS/Supabase) or `docker compose` `db` service. Point `DATABASE_URL` at it.
3. **Secrets** — store in your host’s secret manager / compose env; never commit `.env`.
4. **Run** — `docker compose up -d --build` (includes hourly pipeline worker).
5. **Promote admins** — set `partners.role = 'admin'` in DB for partners who may edit the firm rubric / shared thesis.
6. **Affinity / Clay / Specter** — add keys when ready; pipeline dry-runs those steps until configured.

### Partner onboarding

1. Partner signs in via Clerk → row auto-created in `partners`.
2. They configure **My Thesis** + optional **My Rubric** overlay.
3. Shared pipeline searches the **union** of all active thesis configs (deduped).
4. High **base** scores auto-push to Affinity; each partner’s My Queue is re-ranked by their overlay.

## Make targets

```bash
make migrate
make seed-demo
make api
make frontend
make adapter-test SOURCE=github
```

## API surface

- `GET /api/queue/mine` · `GET /api/queue/team`
- `GET /api/companies/{id}` · feedback · watchlist
- `CRUD /api/me/thesis` · `PUT /api/me/rubric-overlay`
- `GET/POST /api/rubric/base` (POST admin-only)
- `POST /api/pipeline/run` · worker loop via `scripts/run_pipeline_loop.py`
- `POST /api/webhooks/clay`

## Security notes

- `.env` is gitignored. Rotate any key that was ever pasted into chat.
- Keep `AUTH_DEV_BYPASS=false` in shared/staging/prod.
- Clay webhooks verify `CLAY_WEBHOOK_SECRET` when set.
