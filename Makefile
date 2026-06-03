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
	@echo "  containers          docker services"
	@echo "  dev                 start mcp server + client in dev mode (hot reload)"    
	@echo "  inspect             open MCP Inspector for the running HTTP server"
	@echo "  precommit-run       run pre-commit on all files"
	@echo ""
	@echo "  langgraph-dev       start LangGraph dev server with Studio UI (hot reload)"
	@echo "  langgraph-build     build the LangGraph Docker image"
	@echo "  langgraph-up        run LangGraph server via Docker"
	@echo "  langgraph-logs      tail logs from the running LangGraph container"

.PHONY: setup
setup:
	cd mcp-server && ${UV} sync --all-groups
	cd mcp-client && ${UV} sync --all-groups

.PHONY: containers
startup:
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
seed: 
	cd mcp-server && $(UV) run scripts/seeder.py  
	cd mcp-server && $(UV) run scripts/qdrant_seeder.py

.PHONY: langgraph-dev
langgraph-dev:
	cd mcp-client && $(UV) run langgraph dev --config langgraph.json --host 0.0.0.0 --port 2024

.PHONY: up 
up: 
	echo "Starting Docker services..."
.PHONY: precommit-run
precommit-run:
	$(UV) run pre-commit run --all-files

.PHONY: langgraph-build
langgraph-build:
	cd mcp-client && $(UV) run langgraph build --config langgraph.json

.PHONY: langgraph-up
langgraph-up:
	cd mcp-client && $(UV) run langgraph up --config langgraph.json

.PHONY: langgraph-logs
langgraph-logs:
	cd mcp-client && $(UV) run langgraph logs --config langgraph.json