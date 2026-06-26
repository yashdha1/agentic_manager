# MCP Client (Backend Orchestrator)

The MCP Client is the **FastAPI-based backend orchestrator** for the agentics system. It implements the multi-agent architecture using LangGraph, manages state checkpointing, handles memory systems, and exposes REST APIs for the frontend.

## Architecture

### Core Components

```
FastAPI Application
├── REST API Endpoints (/chat, /resume, /history, /health)
├── LangGraph Orchestrator (AgentGraph)
│   ├── Orchestrator Agent (routing)
│   ├── Sales Agent
│   ├── Customer Agent
│   ├── Inventory Agent
│   ├── Knowledge Agent
│   └── Aggregator Agent
├── Memory Systems
│   ├── Long-Term Memory (LTM) — Qdrant vector DB
│   ├── Short-Term Memory (STM) — Redis or in-memory
│   └── Chat Persistence — PostgreSQL
├── State Management (LangGraph Checkpointing)
│   ├── Redis checkpoint store (primary)
│   └── PostgreSQL checkpoint store (fallback)
└── Support Services
    ├── Database (PostgreSQL)
    ├── LLM Providers (Azure OpenAI, Google Gemini)
    ├── Logging & Tracing (LangSmith)
    └── Error Handling & Recovery
```

## Project Structure

```
mcp-client/
├── src/
│   ├── main.py                    # FastAPI app initialization
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── chat.py           # POST /chat - streaming responses
│   │       ├── history.py        # GET /history - conversation history
│   │       ├── resume.py         # POST /resume - interrupt resolution
│   │       └── state.py          # Shared state definitions
│   │
│   ├── core/
│   │   ├── config.py             # Configuration (env variables)
│   │   ├── db.py                 # PostgreSQL connection pool
│   │   ├── logger.py             # Structured logging
│   │   ├── error_handler.py      # Error hierarchy & recovery
│   │   ├── chat_persistence.py   # Chat history storage
│   │   ├── ltm.py                # Long-term memory (Qdrant)
│   │   ├── stm.py                # Short-term memory (Redis/in-memory)
│   │   ├── pg.py                 # PostgreSQL utilities
│   │   ├── qdrant.py             # Qdrant vector DB client
│   │   └── tracing.py            # LangSmith integration
│   │
│   ├── declarative/
│   │   ├── AgentSpec.py          # Agent registry & definitions
│   │   ├── llm.py                # LLM provider abstraction
│   │   ├── workflow.py           # Graph building & agent workflows
│   │   ├── mcp_tools.py          # MCP tool binding
│   │   └── agents/               # Agent system prompts (Markdown)
│   │       ├── Orchestrator.md
│   │       ├── Sales.md
│   │       ├── Customer.md
│   │       ├── Inventory.md
│   │       ├── Knowledge.md
│   │       └── Aggregator.md
│   │
│   └── __init__.py
│
├── eval/
│   ├── evaluate.py               # Evaluation harness
│   ├── generate_dataset.py       # Test case generator
│   ├── dataset.json              # Test cases
│   ├── results.json              # Evaluation results
│   └── contexts/                 # Domain context files
│
├── pyproject.toml               # Dependencies & project metadata
├── README.md                    # This file
└── langgraph.json              # LangGraph studio configuration
```

## Memory Systems

### Long-Term Memory (LTM)

Powered by **Qdrant vector database**. Stores summarized session transcripts for retrieval in future conversations.

- **How it works**: At session end, transcript is summarized via LLM and embedded; stored in Qdrant with metadata
- **Retrieval**: Semantic search on new queries to find relevant past sessions
- **Expiry**: Configurable TTL; old sessions automatically pruned
- **File**: `src/core/ltm.py`

### Short-Term Memory (STM)

Caches context within a single conversation session. Defaults to **Redis**; falls back to **in-memory** if Redis unavailable.

- **Storage**: Agent state, tool results, intermediate outputs
- **TTL**: Session timeout (default: 24 hours)
- **Fallback**: InMemorySTM if Redis unreachable
- **File**: `src/core/stm.py`

### Chat Persistence

**PostgreSQL** stores full conversation history with message content, metadata, and timestamps.

- **Tables**: `chat_threads`, `chat_messages`
- **Access**: `/history` endpoint retrieves paginated chat history
- **File**: `src/core/chat_persistence.py`

## REST API Endpoints

### POST /chat — Start or continue a conversation

**Request:**
```json
{
  "query": "What were the top 5 products sold last quarter?",
  "thread_id": "thread-uuid",  // optional; creates new if absent
  "model": "gpt-4",             // optional; defaults to config
  "metadata": {}                // optional; custom context
}
```

**Response:** Server-Sent Events (SSE) stream

```
data: {"type": "start", "thread_id": "..."}
data: {"type": "agent", "agent": "Orchestrator", "status": "running"}
data: {"type": "token", "agent": "Sales", "content": "Let me..."}
data: {"type": "tool_call", "agent": "Sales", "tool": "query_orders"}
data: {"type": "error", "message": "..."}  // if error occurs
data: {"type": "end", "thread_id": "...", "usage": {...}}
```

### GET /history — Retrieve conversation history

**Query Parameters:**
- `thread_id` (required): Thread UUID
- `limit` (optional, default: 50): Number of messages
- `offset` (optional, default: 0): Pagination offset

**Response:**
```json
{
  "thread_id": "...",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

### POST /resume — Resolve human-in-the-loop interrupts

**Request:**
```json
{
  "thread_id": "...",
  "decisions": [
    {
      "tool_name": "execute_refund",
      "decision": "approve",
      "reasoning": "..."
    }
  ]
}
```

**Response:** SSE stream (same as `/chat`)

### GET /health — Health check

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-06-26T...",
  "services": {
    "database": "ok",
    "redis": "ok",
    "qdrant": "ok",
    "llm": "ok"
  }
}
```

## Agents

Each agent is defined declaratively with:
- **System Prompt** (in `agents/*.md`) — Instructions, capabilities, constraints
- **Tools** — Subset of MCP tools the agent can call
- **Model Tier** — Which LLM to use (flag, light, light-light)

### Agent Descriptions

| Agent | Purpose | Tools | Model |
|-------|---------|-------|-------|
| **Orchestrator** | Route user queries to specialized agents | All (router) | Flag (GPT-4) |
| **Sales** | Revenue analysis, order trends, anomalies | Sales tools | Light |
| **Customer** | Customer support, order inquiries | Customer tools | Light |
| **Inventory** | Stock levels, procurement, availability | Inventory tools | Light |
| **Knowledge** | FAQ, documentation, knowledgebase | Knowledge tools | Light-Light |
| **Aggregator** | Synthesize multi-agent outputs | None (synthesis) | Light |

### Agent State Flow

```
User Input
    ↓
Orchestrator: analyze query → route to agents
    ↓
Parallel Agent Execution:
├─→ Sales Agent: → Tool calls → Results
├─→ Customer Agent: → Tool calls → Results
└─→ Inventory Agent: → Tool calls → Results
    ↓
Aggregator: Combine outputs → Format response
    ↓
Stream to Frontend
```

## State Management & Checkpointing

**LangGraph Checkpointing** enables resumable workflows and interrupt handling:

1. **Checkpoint Store**: Redis (primary) or PostgreSQL (fallback)
2. **Checkpoint Frequency**: After each agent step
3. **Interrupt Handling**: Paused at human-in-the-loop decision points
4. **Resume**: POST to `/resume` with decisions, resumes from checkpoint

## Configuration

See `src/core/config.py` for all settings. Key environment variables:

```bash
# Azure OpenAI
AZURE_API_KEY=...
AZURE_ENDPOINT=https://...
AZURE_API_VERSION=2024-08-01-preview
AZURE_CHAT_FLAG_MODEL=gpt-4-turbo        # Router
AZURE_CHAT_LIGHT_MODEL=gpt-4             # Agent execution
AZURE_EMBEDDING_MODEL=text-embedding-3-small

# Google Gemini (fallback)
GOOGLE_API_KEY=...

# Database
DATABASE_URL=postgresql://user:password@localhost/agentics

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
USE_IN_MEMORY_STM=false  # Use in-memory if Redis unavailable

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...

# Logging
LOG_LEVEL=INFO

# Tracing (optional)
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=agentics
```

## Development

### Running Locally

```bash
# Install dependencies
uv sync

# Run FastAPI server (hot reload)
uv run uvicorn src.main:app --reload --port 8000
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_agents.py -v
```

### Running Evaluation Suite

```bash
# Generate test dataset
uv run python -m eval.generate_dataset

# Run evaluation
uv run python -m eval.evaluate
```

Results saved to `eval/results.json`.

### Debugging

Enable detailed logging:

```bash
LOG_LEVEL=DEBUG uv run uvicorn src.main:app --reload
```

Check LangGraph Studio:

```bash
# Configure langgraph.json with your deployment URL
# Then visit: https://smith.langchain.com/studio
```

## Error Handling

See `src/core/error_handler.py` for custom exception hierarchy:

- **ToolError** — Tool execution failed (retryable)
- **AgentError** — Agent decision-making failed
- **DatabaseError** — Database operation failed
- **LLMError** — LLM provider error
- **ValidationError** — Input validation failed
- **ConfigError** — Configuration error (critical)

All errors are logged with context and converted to user-friendly messages.

## Performance Tuning

### Database Optimization

- Connection pool size: Adjust in `src/core/db.py` based on concurrency
- Query timeouts: Prevent hanging requests (default: 30s)
- Indexes: Ensure chat_threads and chat_messages are indexed

### LLM Optimization

- **Token budgeting**: Use lighter models for non-critical tasks
- **Prompt caching**: Leverage LLM context caching for repeated queries
- **Streaming**: Real-time token streaming for user feedback
- **Fallback models**: Cascade from expensive to cheaper models on failure

### Memory Optimization

- **LTM pruning**: Remove old summaries beyond retention window
- **STM limits**: Cap session memory usage to prevent OOM
- **Checkpoint cleanup**: Archive old checkpoints periodically

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for code standards and contribution process.

## Troubleshooting

### "No module named 'src'"

**Solution**: Ensure you're in the `mcp-client` directory when running:

```bash
cd mcp-client
uv run uvicorn src.main:app --reload
```

### "Connection refused" (Redis/PostgreSQL)

**Solution**: Start containers:

```bash
docker-compose up -d redis postgres
```

Or set `USE_IN_MEMORY_STM=true` to skip Redis.

### "HITL interrupt timeout"

**Solution**: Resume the interrupted conversation via `/resume` endpoint within the timeout window.

### Agent not responding

**Solution**: Check logs for LLM errors:

```bash
LOG_LEVEL=DEBUG uv run uvicorn src.main:app --reload
```

Verify LLM credentials in `.env`.
