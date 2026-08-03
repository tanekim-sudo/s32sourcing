.PHONY: db-up db-down migrate seed seed-demo api frontend adapter-test setup

db-up:
	docker compose up -d

db-down:
	docker compose down

migrate:
	cd backend && .venv/bin/alembic upgrade head

seed:
	cd backend && .venv/bin/python scripts/seed_rubric.py

seed-demo:
	cd backend && .venv/bin/python scripts/seed_demo.py

api:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

adapter-test:
	cd backend && .venv/bin/python scripts/test_adapter.py $(SOURCE)

setup: migrate seed-demo
	@echo "DB migrated + demo seeded. Run: make api  and  make frontend"
