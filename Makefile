SHELL := /bin/bash

ifneq (,$(wildcard .env))
include .env
export
endif

UV             := uv
DOCKER_COMPOSE := docker compose -f docker-compose.yml

.PHONY: help
help:
	@echo "  setup               install deps"
	@echo "  containers          start all Docker services"
	@echo "  dev                 start mcp server in dev mode (hot reload)"
	@echo "  app-dev             start mcp-server + FastAPI backend (LangGraph in-process, hot reload)"
	@echo "  inspect             open MCP Inspector for the running HTTP server"
	@echo "  seed                seed postgres + qdrant"
	@echo "  precommit-run       run pre-commit on all files"

.PHONY: setup
setup:
	cd mcp-server && ${UV} sync --all-groups
	cd mcp-client && ${UV} sync --all-groups

.PHONY: containers
containers:
	$(DOCKER_COMPOSE) up -d

.PHONY: fshut
shutdown:
	$(DOCKER_COMPOSE) down -v --remove-orphans

.PHONY: dev
dev:
	cd mcp-server && $(UV) run fastmcp run src/main.py:mcp --transport http --host 127.0.0.1 --port 9000 --reload

.PHONY: inspect
inspect:
	npx @modelcontextprotocol/inspector http://127.0.0.1:${MCP_SERVER_PORT}/mcp
# 	cd mcp-server && uv run fastmcp inspect src/main.py:mcp

.PHONY: seed
seed: containers
	cd mcp-server && POSTGRES_HOST=localhost QDRANT_HOST=http://localhost $(UV) run scripts/seeder.py
	cd mcp-server && QDRANT_HOST=http://localhost $(UV) run scripts/qdrant_seeder.py

.PHONY: api-dev
api-dev: 
	cd mcp-client && $(UV) run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: up 
up:
	$(DOCKER_COMPOSE) up -d
	@echo "Docker services and project are up."
.PHONY: precommit-run
precommit-run:
	$(UV) run pre-commit run --all-files