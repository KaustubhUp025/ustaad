# One command set for every person and every coding agent (see AGENTS.md).
# Local env comes from backend/.env (copy .env.example) and web/.env.local (copy web/.env.example).
.PHONY: help setup test test-web lint typecheck build check types golden dev-api dev-web mock \
        agent-engine smoke-live deploy-dev deploy-demo deploy-hosting

WEB := $(wildcard web/package.json)
ENVFILE := $(wildcard backend/.env)
MOCKFILES := $(wildcard seed/fixtures/*.json seed/fixtures/*.jsonl)
UVENV := $(if $(ENVFILE),--env-file .env,)

help:            ## list targets
	@grep -E '^[a-z-]+:.*##' Makefile | sed 's/:.*##/ —/'

setup:           ## install backend and web dependencies
	uv sync --directory backend
	@if [ -n "$(WEB)" ]; then pnpm -C web install; fi

test:            ## backend unit tests (offline, fixtures only)
	uv run --directory backend pytest tests/unit -q

test-web:        ## web unit tests (Playwright test runner, no browser)
	@if [ -n "$(WEB)" ]; then pnpm -C web exec playwright test src/; else echo "web/ not scaffolded yet (T04)"; fi

lint:            ## ruff on backend
	uv run --directory backend ruff check .

typecheck:       ## TypeScript typecheck (web)
	@if [ -n "$(WEB)" ]; then pnpm -C web typecheck; else echo "web/ not scaffolded yet (T04)"; fi

build:           ## production web build
	@if [ -n "$(WEB)" ]; then pnpm -C web build; else echo "web/ not scaffolded yet (T04)"; fi

check: lint test test-web typecheck build   ## run before finishing any task

types:           ## export OpenAPI from FastAPI and regenerate web/src/api/types.ts
	uv run --directory backend python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2, sort_keys=True))" > shared/contracts/openapi.json
	@if [ -n "$(WEB)" ]; then pnpm -C web exec openapi-typescript ../shared/contracts/openapi.json -o src/api/types.ts; fi

mock:            ## copy fixtures the web mock mode reads into web/public/mock
	mkdir -p web/public/mock
	@test -n "$(MOCKFILES)" || (echo "no fixtures yet (T09/T10)"; exit 1)
	cp $(MOCKFILES) web/public/mock/

golden:          ## real-model golden paths (costs money; before demo deploys only)
	@if ls backend/tests/golden/test_*.py >/dev/null 2>&1; then cd backend && uv run $(UVENV) pytest tests/golden -q; else echo "no golden tests yet (T29)"; fi

dev-api:         ## run the API locally with backend/.env
	cd backend && uv run $(UVENV) uvicorn app.main:app --reload --port 8080

dev-web:         ## run the PWA locally with web/.env.local
	pnpm -C web dev

agent-engine:    ## create the empty Agent Engine instance for Memory Bank (once)
	cd backend && uv run $(UVENV) python ../infra/agent_engine.py

smoke-live:      ## T05: Live API check in hi/te/ta/bn; LIVE_MODEL=... required
	cd backend && uv run $(UVENV) python ../infra/smoke_live.py

deploy-dev:      ## deploy ustaad-api-dev
	ENV=dev ./infra/deploy.sh

deploy-demo:     ## deploy ustaad-api (A only, from a tag)
	@git describe --exact-match --tags >/dev/null 2>&1 || (echo "checkout a tag first (e.g. v1-rc)"; exit 1)
	ENV=demo ./infra/deploy.sh

deploy-hosting:  ## build web and deploy Firebase Hosting
	pnpm -C web build && firebase deploy --only hosting
