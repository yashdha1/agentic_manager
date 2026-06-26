# AGENTICS - Multi-Agent AI System for E-Commerce Operations

[![Code Quality](https://img.shields.io/badge/ruff-checked-green)](https://docs.astral.sh/ruff/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
[![Node](https://img.shields.io/badge/Node-18+-green)](https://nodejs.org/)

Agentics is a sophisticated **multi-agent AI orchestration system** designed for enterprise e-commerce operations. It combines LangGraph multi-agent orchestration with tool-enabled LLMs to deliver intelligent assistance across sales analytics, inventory management, customer support, and business intelligence.

## Features

- 🤖 **Multi-Agent Architecture** — Specialized agents for Sales, Customers, Inventory, Knowledge, and Analytics
- 🔧 **Tool-Enabled LLMs** — MCP-based tool execution with 15+ integrated business tools
- 💾 **Hybrid Memory System** — Long-term memory (vector DB), short-term memory (Redis), and chat persistence (PostgreSQL)
- 🚀 **Streaming Responses** — Real-time agent reasoning and tool execution visibility
- 🔄 **State Management** — LangGraph checkpoints for resumable workflows and interruption handling
- 📊 **Multi-Provider LLMs** — Support for Azure OpenAI, Google Gemini with fallback strategies
- 🛡️ **Error Recovery** — Graceful fallbacks with exponential backoff and logging

## Quick Start

### Prerequisites

- Docker & Docker Compose
- `uv` package manager (Python)
- Node.js 18+ (frontend)

### 1. Setup

```bash
make setup
```

This installs Python dependencies via `uv` for both `mcp-client` and `mcp-server`, and Node dependencies for frontend.

### 2. Start Infrastructure

```bash
make up
```

Starts PostgreSQL 16, Qdrant (vector DB), Redis, MCP server, FastAPI backend, and Next.js frontend.

### 3. Seed Data

```bash
make seed
```

Populates PostgreSQL with sample e-commerce data (orders, customers, products) and Qdrant with knowledge vectors.

### 4. Access the System

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000 (OpenAPI docs at `/docs`)
- **MCP Server**: http://localhost:9000/mcp

## Project Structure

```
agentics/
├── mcp-server/              # MCP tool provider
│   ├── src/
│   │   ├── tools/          # Business logic (Sales, Customers, Inventory, etc.)
│   │   ├── resources/      # Data access layer
│   │   ├── prompts/        # System prompts for tools
│   │   └── main.py         # MCP server entry point
│   ├── dataset/            # Sample CSV data
│   └── scripts/            # Data seeding scripts
│
├── mcp-client/              # FastAPI orchestrator + LangGraph agents
│   ├── src/
│   │   ├── api/            # REST API endpoints (chat, resume, history)
│   │   ├── core/           # Core services
│   │   │   ├── db.py       # Database connection pool
│   │   │   ├── logger.py   # Structured logging
│   │   │   ├── config.py   # Configuration + LLM settings
│   │   │   ├── error_handler.py  # Error hierarchy & recovery
│   │   │   ├── chat_persistence.py  # PostgreSQL chat history
│   │   │   ├── ltm.py      # Long-term memory (vector)
│   │   │   ├── stm.py      # Short-term memory (Redis/in-memory)
│   │   │   └── tracing.py  # LangSmith integration
│   │   └── declarative/    # Agent definitions (YAML-based)
│   │       ├── agents/     # Agent system prompts
│   │       ├── AgentSpec.py # Agent registry
│   │       └── mcp_tools.py # MCP tool binding
│   └── eval/               # Evaluation suite + test dataset
│
├── frontend/                # Next.js 16 web UI
│   ├── app/
│   │   ├── page.tsx        # Home page
│   │   └── api/[..._path]/ # API proxy routes
│   ├── components/
│   │   ├── thread/         # Chat interface & history
│   │   ├── ui/             # Radix UI components
│   │   └── icons/          # SVG icons
│   ├── lib/
│   │   ├── api.ts          # API client + SSE handling
│   │   ├── error-recovery.ts  # Retry logic & error handling
│   │   └── utils.ts        # Utilities
│   └── public/             # Static assets
│
├── docker-compose.yml       # Infrastructure (PostgreSQL, Qdrant, Redis)
├── Makefile                 # Development commands
├── ruff.toml               # Python linting rules
└── biome.json              # Frontend formatting rules
```

## Architecture

### System Flow

```
User Query → Frontend (Next.js) → Backend API (FastAPI) → LangGraph Orchestrator
                                                             ↓
                                                    Routing to Specialized Agents
                                                    (Sales, Customers, Inventory, etc.)
                                                             ↓
                                                    Tool Execution via MCP
                                                    (Database queries, API calls)
                                                             ↓
                                                    Memory Updates (LTM, STM)
                                                             ↓
                                                    Response Streaming to Frontend
```

### Key Components

| Component | Purpose | Technology |
|-----------|---------|-----------|
| **Frontend** | Chat UI, streaming responses, artifact rendering | Next.js 16, React 19, TailwindCSS, Radix UI |
| **Backend API** | REST endpoints for chat, history, interrupt handling | FastAPI, Pydantic |
| **LangGraph Orchestrator** | Multi-agent coordination, state management, checkpointing | LangGraph 0.1+, Redis/PostgreSQL checkpoint store |
| **Specialized Agents** | Domain-specific reasoning and tool selection | LLM prompts (Azure OpenAI, Google Gemini) |
| **MCP Server** | Tool exposure and execution | MCP 1.0 protocol |
| **Database** | Chat history, user data, business data | PostgreSQL 16 |
| **Vector DB** | Semantic search and long-term memory | Qdrant |
| **Cache/Session Store** | Short-term memory, checkpoint storage | Redis |

## Common Tasks

### Run Backend in Dev Mode (hot reload)

```bash
make api-dev
```

### Run Frontend in Dev Mode

```bash
cd frontend && npm run dev  # or pnpm dev
```

### Run MCP Server in Dev Mode

```bash
make dev
```

### Inspect MCP Tools

```bash
make inspect
```

Opens MCP Inspector to test tools against the running MCP server.

### Run Code Quality Checks

```bash
ruff check .
ruff format --check .
tsc --noEmit  # TypeScript check
eslint frontend/
```

Auto-fix issues:

```bash
ruff check --fix .
ruff format .
```

### Stop & Clean Up

```bash
make shutdown
```

### View Available Commands

```bash
make help
```

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings:
- `AZURE_API_KEY`, `AZURE_ENDPOINT` — Azure OpenAI credentials
- `GOOGLE_API_KEY` — Google Gemini API key (fallback)
- `REDIS_HOST`, `REDIS_PORT` — Redis connection
- `DATABASE_URL` — PostgreSQL connection string
- `QDRANT_URL`, `QDRANT_API_KEY` — Qdrant vector DB
- `LANGSMITH_API_KEY` — (Optional) LangSmith tracing

## Troubleshooting

### Backend won't start: "Redis connection refused"

**Solution**: Ensure Redis is running:

```bash
docker-compose up -d redis
```

Or set `USE_IN_MEMORY_STM=true` to use in-memory short-term memory instead.

### "LLM model not found" errors

**Solution**: Verify Azure credentials and model names in `.env`:

```bash
AZURE_CHAT_FLAG_MODEL=gpt-4-turbo
AZURE_CHAT_LIGHT_MODEL=gpt-4
AZURE_EMBEDDING_MODEL=text-embedding-3-small
```

### Frontend can't reach backend API

**Solution**: Check that backend is running on port 8000:

```bash
curl http://localhost:8000/health
```

If using Docker, ensure frontend container has correct API_URL environment variable.

### Database migration errors

**Solution**: Check PostgreSQL is running and reset migrations:

```bash
make shutdown  # Clean up
make up        # Start fresh
make seed      # Re-seed data
```

### Qdrant connectivity issues

**Solution**: Verify Qdrant is reachable:

```bash
curl http://localhost:6333/health
```

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) — Detailed system design and component interactions
- [API.md](./API.md) — REST API documentation with examples
- [mcp-client/README.md](./mcp-client/README.md) — Agent architecture and state flow
- [mcp-server/README.md](./mcp-server/README.md) — MCP tool schema and contribution guide
- [CONTRIBUTING.md](./CONTRIBUTING.md) — Coding standards and contribution process

## Development Workflow

1. **Create a feature branch**: `git checkout -b feature/my-feature`
2. **Make changes** and test locally
3. **Run code quality checks**: `ruff check . && ruff format .`
4. **Run tests**: `pytest mcp-client/` (when available)
5. **Commit and push**: `git push origin feature/my-feature`
6. **Open a PR** for review

## Evaluation & Testing

The project includes an evaluation suite in `mcp-client/eval/`:

```bash
cd mcp-client
python -m eval.evaluate  # Run evaluation suite
```

Results are saved to `eval/results.json` with metrics on agent accuracy, latency, and cost.

## Performance Considerations

- **Token Budgeting**: Flag model (GPT-4) for routing, light models for execution
- **Caching**: Tool responses cached for 5-60s depending on domain
- **Streaming**: Responses streamed for real-time feedback
- **Checkpointing**: Agent state saved to Redis with PostgreSQL fallback
- **Vector Search**: Semantic search in Qdrant limited to top-10 results

## License

Proprietary — All rights reserved.

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs: `docker-compose logs mcp-client` or `docker-compose logs frontend`
3. Check PostgreSQL: `docker-compose exec postgres psql -U postgres -d agentics`
4. Create an issue with reproduction steps

## Notes

- Keep your `.env` values aligned with `docker-compose.yml` service names and ports.
- If service startup order causes transient failures, rerun `make up` once dependencies are healthy.