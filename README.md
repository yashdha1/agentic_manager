# AGENTIC - SMART MANAGER FOR YOUR BUSINESS

Agentic is a multi-service project for building and running a tool-enabled AI assistant system.
It includes:
- an MCP server for tool exposure,
- a Python backend client/orchestrator,
- a Next.js frontend,
- and supporting infrastructure (PostgreSQL, Qdrant, Redis).

## Project Structure

- `mcp-server`: MCP tools, prompts, and data seeding scripts.
- `mcp-client`: FastAPI backend with orchestration logic.
- `frontend`: Next.js web UI.
- `docker-compose.yml`: local containerized stack for infra + services.
- `Makefile`: common commands for setup, run, and seeding.

## Prerequisites

- Docker and Docker Compose
- `uv` package manager
- Node.js (for frontend and MCP inspector)

## Setup

Run dependency installation for both Python services:

```bash
make setup
```

## Run The Project

Start all Docker services and project containers:

```bash
make up
```

Run the MCP server in local dev mode (hot reload):

```bash
make dev
```

Run the FastAPI backend locally in dev mode (hot reload):

```bash
make api-dev
```

## Seed Data

Seed PostgreSQL and Qdrant using project scripts:

```bash
make seed
```

This command ensures required containers are running and then executes:
- `mcp-server/scripts/seeder.py` for relational dataset seeding,
- `mcp-server/scripts/qdrant_seeder.py` for vector knowledge seeding.

## Useful Commands

- `make help`: list available make targets.
- `make containers`: start all docker services in detached mode.
- `make shutdown`: stop and remove containers, volumes, and orphans.
- `make inspect`: open MCP Inspector against the running MCP endpoint.
- `make precommit-run`: run pre-commit checks on all files.

## Typical Local Workflow

1. `make setup`
2. `make up`
3. `make seed`
4. Open frontend at `http://localhost:3000`
5. Backend API should be available at `http://localhost:8000`
6. MCP server should be available at `http://localhost:9000/mcp`

## Notes

- Keep your `.env` values aligned with `docker-compose.yml` service names and ports.
- If service startup order causes transient failures, rerun `make up` once dependencies are healthy.