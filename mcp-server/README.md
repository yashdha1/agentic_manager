# MCP Server - Tool Provider

The MCP Server exposes **15+ business tools** via the **Model Context Protocol (MCP)**, enabling LLMs and agents to query databases, execute operations, and retrieve business information across sales, inventory, customers, and knowledge domains.

## Overview

The MCP Server implements the MCP 1.0 specification and provides tools for:

- 📊 **Sales Analytics** — Revenue analysis, order trends, payment methods, anomalies
- 👥 **Customer Operations** — Support queries, order lookups, newsletter management
- 📦 **Inventory Management** — Stock levels, reorder points, procurement recommendations
- 📚 **Knowledge Base** — FAQ search, documentation, business intelligence

## Architecture

```
MCP Server (FastAPI)
├── Tool Definitions (MCP Protocol)
├── Business Logic (Tools)
├── Data Access Layer (Resources)
├── Database Connection (PostgreSQL)
├── Dataset Seeding (CSV files)
└── Prompts & System Messages
```

## Project Structure

```
mcp-server/
├── src/
│   ├── main.py                    # MCP server entry point
│   │
│   ├── tools/                     # Tool implementations
│   │   ├── sales_tools/
│   │   │   ├── Queries.py        # Sales read operations
│   │   │   ├── Analytics.py      # Aggregations, trends
│   │   │   └── Anomalies.py      # Anomaly detection
│   │   ├── customers_tools/
│   │   │   ├── Queries.py        # Customer lookups
│   │   │   └── Operations.py     # Support, refunds, etc.
│   │   ├── inventory_tools/
│   │   │   ├── Queries.py        # Stock levels
│   │   │   └── Procurement.py    # Reorder points
│   │   └── knowledge_tools/
│   │       └── Search.py         # KB search
│   │
│   ├── resources/                 # Data access layer
│   │   ├── customers.py
│   │   ├── orders.py
│   │   ├── products.py
│   │   ├── reviews.py
│   │   └── knowledgebase.py
│   │
│   ├── prompts/                   # System messages & examples
│   │   └── *.md                   # Prompt templates
│   │
│   └── core/
│       ├── config.py
│       ├── db.py
│       ├── logger.py
│       └── error_handler.py
│
├── dataset/                       # Sample CSV data
│   ├── customers.csv
│   ├── products.csv
│   ├── orders.csv
│   ├── order_items.csv
│   ├── reviews.csv
│   ├── inventory_events.csv
│   ├── refunds.csv
│   └── knowledgebase.csv
│
├── scripts/                       # Seeding & utilities
│   ├── seeder.py                 # PostgreSQL data seeding
│   ├── qdrant_seeder.py          # Vector DB seeding
│   └── generate_dataset.py       # Synthetic data generation
│
├── alembic/                       # Database migrations
│   └── versions/                 # Migration scripts
│
├── pyproject.toml               # Dependencies
├── README.md                    # This file
└── alembic.ini                  # Alembic config
```

## Tools Reference

### Sales Tools

#### `query_sales_metrics`
Get high-level sales metrics for a date range.

**Parameters:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "metric": "revenue" // "revenue" | "order_count" | "avg_order_value"
}
```

**Returns:**
```json
{
  "metric": "revenue",
  "value": 150000.50,
  "currency": "USD",
  "period": "2024-01-01 to 2024-01-31"
}
```

#### `query_orders`
Search and filter orders.

**Parameters:**
```json
{
  "customer_id": null,
  "status": "completed",        // "pending" | "completed" | "refunded"
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "limit": 100,
  "offset": 0
}
```

**Returns:**
```json
{
  "orders": [
    {
      "order_id": "ORD-001",
      "customer_id": "CUST-123",
      "total_amount": 250.00,
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "items": [...]
    }
  ],
  "total": 250,
  "limit": 100,
  "offset": 0
}
```

#### `analyze_sales_trend`
Analyze sales trends over time.

**Parameters:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "granularity": "monthly"       // "daily" | "weekly" | "monthly"
}
```

**Returns:**
```json
{
  "granularity": "monthly",
  "data": [
    {"date": "2024-01-01", "revenue": 15000, "orders": 50},
    {"date": "2024-02-01", "revenue": 18000, "orders": 60}
  ],
  "total_revenue": 180000,
  "total_orders": 1200,
  "avg_order_value": 150.00
}
```

#### `detect_sales_anomalies`
Identify unusual patterns in sales data.

**Parameters:**
```json
{
  "window_days": 30,
  "threshold_std_dev": 2.0
}
```

**Returns:**
```json
{
  "anomalies": [
    {
      "date": "2024-01-20",
      "type": "spike",
      "revenue": 500000,
      "expected": 15000,
      "std_dev": 10.5
    }
  ]
}
```

### Customer Tools

#### `get_customer_info`
Retrieve customer details.

**Parameters:**
```json
{
  "customer_id": "CUST-123"
}
```

**Returns:**
```json
{
  "customer_id": "CUST-123",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1-234-567-8900",
  "created_at": "2023-06-15T...",
  "total_purchases": 25,
  "lifetime_value": 5000.00
}
```

#### `query_customer_orders`
Get orders for a specific customer.

**Parameters:**
```json
{
  "customer_id": "CUST-123",
  "limit": 50
}
```

**Returns:** Array of orders (same as `query_orders`)

#### `submit_refund_request`
Create a refund for an order.

**Parameters:**
```json
{
  "order_id": "ORD-001",
  "reason": "damaged_product",    // "damaged_product" | "not_as_described" | "changed_mind"
  "amount": 100.00
}
```

**Returns:**
```json
{
  "refund_id": "REF-001",
  "order_id": "ORD-001",
  "amount": 100.00,
  "status": "pending_approval",
  "created_at": "2024-06-26T..."
}
```

#### `send_newsletter`
Send a newsletter to subscribers.

**Parameters:**
```json
{
  "subject": "Summer Sale!",
  "content": "Check out our latest deals...",
  "recipient_segment": "all"      // "all" | "vip" | "inactive"
}
```

**Returns:**
```json
{
  "status": "sent",
  "recipient_count": 5000,
  "message_id": "MSG-001"
}
```

### Inventory Tools

#### `check_stock_level`
Get current stock for a product.

**Parameters:**
```json
{
  "product_id": "PROD-123"
}
```

**Returns:**
```json
{
  "product_id": "PROD-123",
  "product_name": "Widget",
  "current_stock": 500,
  "reorder_point": 100,
  "reorder_quantity": 200,
  "last_restock": "2024-06-20T..."
}
```

#### `query_low_stock_items`
Find items below reorder points.

**Parameters:**
```json
{
  "limit": 50
}
```

**Returns:**
```json
{
  "items": [
    {
      "product_id": "PROD-123",
      "name": "Widget",
      "current_stock": 50,
      "reorder_point": 100,
      "days_until_stockout": 5
    }
  ],
  "total": 12
}
```

#### `recommend_procurement`
Get procurement recommendations.

**Parameters:**
```json
{
  "product_id": "PROD-123",
  "forecast_days": 30
}
```

**Returns:**
```json
{
  "product_id": "PROD-123",
  "recommendation": "order_now",
  "suggested_quantity": 500,
  "reason": "Low stock projected to last 5 days",
  "estimated_cost": 5000.00
}
```

### Knowledge Tools

#### `search_knowledgebase`
Search the knowledge base via semantic search.

**Parameters:**
```json
{
  "query": "How do I return a product?",
  "limit": 5
}
```

**Returns:**
```json
{
  "results": [
    {
      "id": "KB-001",
      "title": "Return Policy",
      "content": "We accept returns within 30 days...",
      "relevance_score": 0.95
    }
  ]
}
```

## Tool Schemas

Tools follow MCP protocol with:

```python
{
  "name": "query_sales_metrics",
  "description": "Get high-level sales metrics for a date range.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "start_date": {"type": "string", "description": "YYYY-MM-DD format"},
      "end_date": {"type": "string", "description": "YYYY-MM-DD format"},
      "metric": {"type": "string", "enum": ["revenue", "order_count", ...]}
    },
    "required": ["start_date", "end_date", "metric"]
  }
}
```

## Database Schema

Key tables exposed via tools:

```sql
customers (id, name, email, phone, created_at, ...)
products (id, name, sku, price, category, ...)
orders (id, customer_id, total_amount, status, created_at, ...)
order_items (id, order_id, product_id, quantity, unit_price, ...)
reviews (id, product_id, customer_id, rating, content, ...)
inventory_events (product_id, event_type, quantity, timestamp, ...)
refunds (id, order_id, amount, status, reason, created_at, ...)
knowledgebase (id, title, content, category, ...)
```

## Setup & Development

### Install Dependencies

```bash
cd mcp-server
uv sync
```

### Run Server Locally

```bash
uv run uvicorn src.main:app --reload --port 9000
```

### Run MCP Inspector

```bash
# From project root
make inspect
```

This opens the MCP Inspector UI for testing tools.

### Seed Database

```bash
# Populate PostgreSQL with sample data
cd mcp-server
uv run python scripts/seeder.py

# Populate Qdrant with knowledge vectors
uv run python scripts/qdrant_seeder.py
```

### Generate Synthetic Data

```bash
uv run python scripts/generate_dataset.py --customers 10000 --orders 50000
```

## Database Migrations

Migrations are managed with Alembic:

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Adding New Tools

To add a new tool:

1. **Create tool module** in `src/tools/` (e.g., `src/tools/reporting_tools/Reports.py`)

2. **Implement tool function** with proper typing:

```python
from typing import Any

async def generate_sales_report(
    start_date: str,
    end_date: str,
    format: str = "json"
) -> dict[str, Any]:
    """Generate a comprehensive sales report.
    
    Args:
        start_date: YYYY-MM-DD format
        end_date: YYYY-MM-DD format
        format: Output format (json, csv, pdf)
    
    Returns:
        Report data and metadata
    """
    # Implementation
    pass
```

3. **Register tool in `src/main.py`**:

```python
tools = [
    {
        "name": "generate_sales_report",
        "description": "Generate a comprehensive sales report...",
        "inputSchema": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }
]
```

4. **Add handler in `src/main.py`**:

```python
async def handle_tool_call(name: str, arguments: dict) -> Any:
    if name == "generate_sales_report":
        return await reports.generate_sales_report(**arguments)
    # ...
```

5. **Test with MCP Inspector**:

```bash
make inspect
```

## Error Handling

All tools handle errors gracefully:

- **Database errors** → Logged and returned as failed result
- **Validation errors** → Return detailed error message
- **Timeout errors** → Return timeout error with retry suggestion
- **Authorization errors** → Return permission denied

See `src/core/error_handler.py` for error hierarchy.

## Performance Tuning

### Query Optimization

- Add indexes on frequently queried columns
- Use LIMIT/OFFSET for pagination
- Avoid N+1 queries with JOINs

### Caching

- Cache tool results for 5-60s depending on freshness requirements
- Use Redis for frequently accessed data
- Invalidate cache on data mutations

### Connection Pooling

- PostgreSQL connection pool size: Adjust in `src/core/db.py`
- Qdrant connection limits: Configure in deployment

## Troubleshooting

### "No database connection"

**Solution**: Ensure PostgreSQL is running:

```bash
docker-compose up -d postgres
```

### "Tool not found" in MCP Inspector

**Solution**: Ensure tool is registered in `src/main.py` and server is restarted.

### Slow query

**Solution**: Check PostgreSQL slow query log:

```bash
docker-compose exec postgres psql -U postgres -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

Add indexes as needed.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for code standards.

When adding tools:
1. Write comprehensive docstrings
2. Include input validation
3. Add error handling
4. Test with MCP Inspector
5. Update this README with tool documentation
