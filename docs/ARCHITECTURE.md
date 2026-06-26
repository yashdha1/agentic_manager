# System Architecture

This document describes the high-level architecture of the agentics system, including component interactions, data flow, and design decisions.

## System Overview

Agentics is a **multi-agent AI orchestration system** that processes natural language queries through specialized agents, which leverage business tools to retrieve and manipulate data, ultimately delivering intelligent responses back to the user.

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                         │
│                      Next.js Frontend (3000)                    │
└────────────────────────────────────┬────────────────────────────┘
                                     │ HTTP/SSE
                                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                       FASTAPI BACKEND (8000)                    │
│  ├─ /chat          → Streaming chat endpoint                  │
│  ├─ /history       → Retrieve conversation history            │
│  ├─ /resume        → Handle HITL interrupts                   │
│  └─ /health        → Service health check                     │
└────────────────────────────────────┬────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ↓                ↓                ↓
        ┌──────────────────┐  ┌────────────────┐  ┌───────────────┐
        │  LANGGRAPH       │  │  STATE STORE   │  │  MEMORY LAYER │
        │  ORCHESTRATOR    │  │                │  │               │
        │                  │  │  Redis (hot)   │  │  LTM (Qdrant) │
        │ - Orchestrator   │  │  PG (fallback) │  │  STM (Redis)  │
        │   Agent          │  │                │  │  Chat (PG)    │
        │ - Sales Agent    │  └────────────────┘  └───────────────┘
        │ - Customer Agent │
        │ - Inventory Ag.  │
        │ - Knowledge Ag.  │
        │ - Aggregator Ag. │
        └────────┬─────────┘
                 │ MCP Calls
                 ↓
        ┌──────────────────────────┐
        │   MCP SERVER (9000)      │
        │                          │
        │  Sales Tools             │
        │  ├─ query_sales_metrics  │
        │  ├─ query_orders         │
        │  └─ detect_anomalies     │
        │                          │
        │  Customer Tools          │
        │  ├─ get_customer_info    │
        │  └─ submit_refund        │
        │                          │
        │  Inventory Tools         │
        │  ├─ check_stock          │
        │  └─ recommend_procurement│
        │                          │
        │  Knowledge Tools         │
        │  └─ search_knowledgebase │
        └────────┬─────────────────┘
                 │ SQL Queries
                 ↓
        ┌──────────────────┐
        │   PostgreSQL     │
        │   (Business Data)│
        └──────────────────┘
```

## Core Components

### 1. Frontend (Next.js 16)

**Location**: `frontend/`

**Responsibilities**:
- User interface for chat interactions
- Real-time streaming response display
- Conversation history browsing
- Artifact rendering (code, markdown, tables)
- Error handling and retry UI

**Key Technologies**:
- React 19, TailwindCSS 4, Radix UI
- Server-Sent Events (SSE) for streaming
- TypeScript for type safety

**Interaction Pattern**:
```
User Input → /chat endpoint (SSE) → Stream tokens → Display response
                                  → Retry on error with backoff
```

### 2. FastAPI Backend (Port 8000)

**Location**: `mcp-client/src/api/`

**Responsibilities**:
- REST API for chat, history, interrupts
- Request validation and error handling
- SSE response streaming
- Session and state management

**Key Endpoints**:
- `POST /chat` — Stream chat response
- `GET /history` — Retrieve conversation history
- `POST /resume` — Resolve human-in-the-loop (HITL) interrupts
- `GET /health` — Service health check

**Error Handling**:
- Catches exceptions from orchestrator
- Converts to user-friendly messages
- Logs with context for debugging
- Returns appropriate HTTP status codes

### 3. LangGraph Orchestrator

**Location**: `mcp-client/src/declarative/`

**Responsibilities**:
- Multi-agent coordination
- Agent selection and routing
- Tool invocation and result aggregation
- State checkpointing for resumable workflows
- Human-in-the-loop (HITL) interrupt handling

**Agent Hierarchy**:

```
Orchestrator Agent (Routing)
├─→ Route to specialized agents
├─→ Parse tool requirements
└─→ Aggregate results via Aggregator

Specialized Agents (Parallel Execution)
├─ Sales Agent
│  ├─→ Analyze revenue trends
│  ├─→ Query order data
│  └─→ Detect anomalies
├─ Customer Agent
│  ├─→ Retrieve customer info
│  ├─→ Process refund requests
│  └─→ Send communications
├─ Inventory Agent
│  ├─→ Check stock levels
│  ├─→ Generate reorder recommendations
│  └─→ Monitor inventory changes
└─ Knowledge Agent
   └─→ Search knowledgebase

Aggregator Agent (Synthesis)
└─→ Combine outputs into coherent response
```

**Execution Flow**:

```
1. User Query
   ↓
2. Orchestrator: Analyze intent, route to agents
   ↓
3. Parallel Agent Execution:
   - Sales: Call tools → Get results
   - Customer: Call tools → Get results
   - Inventory: Call tools → Get results
   ↓
4. Aggregator: Synthesize outputs
   ↓
5. Response to User
```

### 4. MCP Server (Port 9000)

**Location**: `mcp-server/src/`

**Responsibilities**:
- Tool exposure via MCP protocol
- Business logic implementation
- Database query execution
- Data validation and transformation

**Tool Categories**:
- Sales: Metrics, trends, anomalies
- Customers: Info, orders, refunds, communications
- Inventory: Stock levels, reorder points, procurement
- Knowledge: Knowledge base search

**MCP Protocol**:
- Tools exposed as callable functions with schemas
- Supports both read and write operations
- Includes error handling and validation

### 5. State Management

**Short-Term Memory (STM)**: `mcp-client/src/core/stm.py`

- **Storage**: Redis (primary) or in-memory (fallback)
- **Content**: Agent state, tool results, intermediate outputs
- **TTL**: Session timeout (default: 24 hours)
- **Purpose**: Fast access to current session context

**Long-Term Memory (LTM)**: `mcp-client/src/core/ltm.py`

- **Storage**: Qdrant vector database
- **Content**: Summarized session transcripts
- **TTL**: Configurable expiry (default: 30 days)
- **Purpose**: Retrieve relevant context from past sessions

**Chat Persistence**: `mcp-client/src/core/chat_persistence.py`

- **Storage**: PostgreSQL (tables: chat_threads, chat_messages)
- **Content**: Full conversation history with metadata
- **Purpose**: User-facing history, audit trail, training data

**State Checkpointing**: LangGraph checkpoints

- **Storage**: Redis (primary) or PostgreSQL (fallback)
- **Purpose**: Enable resumable workflows and HITL interrupts
- **Frequency**: After each agent step

### 6. Databases

#### PostgreSQL (Primary Data Store)

**Tables**:
- `customers` — Customer information
- `products` — Product catalog
- `orders`, `order_items` — Order data
- `reviews` — Product reviews
- `refunds` — Refund transactions
- `inventory_events` — Stock movements
- `knowledgebase` — FAQ/documentation
- `chat_threads`, `chat_messages` — Conversation history
- `ltm_summaries` — LTM metadata (Qdrant collections)

**Indexes**: Optimized for common queries (customer_id, order_status, product_id, created_at)

#### Qdrant (Vector Database)

**Collections**:
- `ltm_summaries` — Session summaries for semantic search
- `knowledgebase_embeddings` — Knowledge base vectors

**Search**: Semantic similarity (cosine distance)

#### Redis (Session Store & Cache)

**Keys**:
- `session:{thread_id}` — Current session state (STM)
- `checkpoint:{thread_id}:{step}` — LangGraph checkpoints
- `cache:{tool_name}:{params_hash}` — Tool result cache

**TTL**: Session-based (auto-expire after inactivity)

## Data Flow Examples

### Example 1: Sales Query

```
1. User: "What were our top products by revenue last month?"
                           │
                           ↓
2. Frontend: POST /chat with query
                           │
                           ↓
3. Backend: Validate input, create thread
                           │
                           ↓
4. Orchestrator: Route to Sales Agent
                           │
                           ↓
5. Sales Agent: 
   - Determine date range (last month)
   - Call MCP: query_orders(status="completed")
   - Call MCP: query_sales_metrics(metric="revenue", groupby="product")
   - Process results: top products by revenue
                           │
                           ↓
6. Aggregator: Format results as natural language
                           │
                           ↓
7. Response: Stream to frontend as tokens
   "Based on last month's data, our top products by revenue were:
    1. Premium Widget: $500K
    2. Standard Widget: $300K
    ..."
                           │
                           ↓
8. Frontend: Display streaming response
                           │
                           ↓
9. Persistence:
   - Save to chat_messages (PostgreSQL)
   - Update STM with context
   - (Optionally) Update LTM with summary
```

### Example 2: Human-in-the-Loop Interrupt

```
1. Agent proposes: execute_refund(order_id=123, amount=$500)
                           │
                           ↓
2. Orchestrator: Interrupt workflow, request human approval
                           │
                           ↓
3. Frontend: Display refund request to user
                           │
                           ↓
4. User: Approves/rejects decision
                           │
                           ↓
5. Frontend: POST /resume with decision
                           │
                           ↓
6. Backend: Load checkpoint, resume from interruption point
                           │
                           ↓
7. Orchestrator: Execute approved tool or alternative path
                           │
                           ↓
8. Response: Notify user of outcome
```

## Error Handling & Recovery

### Error Hierarchy

```
AgenticsError (base)
├─ ToolError (tool execution failed)
├─ AgentError (agent decision-making failed)
├─ DatabaseError (DB operation failed, retryable)
├─ LLMError (LLM provider error, retryable)
├─ ValidationError (input validation failed)
└─ ConfigError (configuration error, critical)
```

### Recovery Strategies

1. **Retryable Errors**: Exponential backoff (1s → 2s → 4s → 8s)
2. **Non-retryable Errors**: Fail fast, return user-friendly message
3. **Fallback Models**: Cascade from expensive to cheaper LLM models
4. **In-Memory Fallback**: Use in-memory STM if Redis unavailable
5. **PostgreSQL Fallback**: Use PostgreSQL checkpoints if Redis unavailable

### Logging

All errors logged with:
- Error type and message
- Severity level (critical, high, medium, low)
- Context (thread_id, agent_name, tool_name)
- Structured JSON format for parsing

## Performance Considerations

### Latency Targets

- **First token**: <2 seconds
- **Full response**: <30 seconds
- **Tool execution**: <10 seconds per tool
- **Database query**: <5 seconds

### Optimization Strategies

1. **Streaming**: Stream tokens as they arrive for real-time feedback
2. **Parallel Agents**: Execute specialized agents in parallel
3. **Caching**: Cache tool results (5-60s TTL)
4. **Query Optimization**: Use indexes, pagination, selective fields
5. **Model Selection**: Use lighter models for non-critical tasks
6. **Connection Pooling**: Reuse database connections

### Cost Optimization

- **Token Budgeting**: Flag model (expensive) for routing; light models for execution
- **Context Window**: Keep STM limited to reduce token cost
- **Prompt Caching**: Leverage LLM context caching for repeated queries
- **Selective LTM**: Only summarize and store important sessions

## Deployment Architecture

### Docker Compose (Development)

```yaml
Services:
- PostgreSQL 16 (port 5432)
- Qdrant (port 6333)
- Redis (port 6379)
- MCP Server (port 9000)
- FastAPI Backend (port 8000)
- Next.js Frontend (port 3000)

Volumes:
- PostgreSQL data
- Qdrant data
- Redis data
```

### Production (Kubernetes / Cloud)

```
Ingress
├─ Frontend Pod (replicas: 3)
├─ Backend Pod (replicas: 2-5 auto-scaling)
├─ MCP Server Pod (replicas: 1-3)
└─ Infrastructure
   ├─ PostgreSQL (managed service)
   ├─ Qdrant (statefulset or managed)
   └─ Redis (statefulset or managed)
```

## Security Considerations

### Authentication

- API requests validated (currently single-user; multi-user auth can be added)
- Environment variables for sensitive credentials (.env file)

### Authorization

- Tool access restricted per agent (agents only access assigned tools)
- HITL interrupts require user approval for sensitive operations

### Data Protection

- All connections use encryption (TLS/SSL in production)
- PostgreSQL encryption at rest (optional)
- Sensitive data masked in logs

## Future Enhancements

1. **Multi-User Support**: JWT auth, user isolation, rate limiting
2. **Advanced Monitoring**: Metrics collection, alerting, dashboards
3. **Audit Logging**: Complete audit trail for compliance
4. **Tool Versioning**: Support multiple versions of tools
5. **Custom Agents**: Allow users to define custom agents
6. **Plugin System**: Third-party tool integration
7. **Cost Tracking**: Per-user/query cost tracking
8. **A/B Testing**: Experiment with different agent strategies
