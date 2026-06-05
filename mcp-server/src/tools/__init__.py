from fastmcp import FastMCP

from .customers_tools import Command, Queries
from .inventory_tools import Command as InventoryCommand
from .inventory_tools import Queries_inventory_event as InventoryEventQueries
from .inventory_tools import Queries_refund as InventoryRefundQueries
from .knowledge_tools import Command as KnowledgeCommand
from .knowledge_tools import Queries as KnowledgeQueries
from .orchestrator_tools import Query as OrchestratorQuery
from .sales_tools import Analyze as SalesAnalyze
from .sales_tools import Command as SalesCommand
from .sales_tools import Queries_orders as SalesOrderQueries
from .sales_tools import Queries_sales as SalesQueries

mcp = FastMCP("ecomm_mcp_customer_tools")

mcp.mount(Command.mcp)
mcp.mount(Queries.mcp)
mcp.mount(SalesQueries.mcp)
mcp.mount(SalesOrderQueries.mcp)
mcp.mount(SalesAnalyze.mcp)
mcp.mount(SalesCommand.mcp)
mcp.mount(InventoryCommand.mcp)
mcp.mount(InventoryEventQueries.mcp)
mcp.mount(InventoryRefundQueries.mcp)
mcp.mount(OrchestratorQuery.mcp)
mcp.mount(KnowledgeQueries.mcp)
mcp.mount(KnowledgeCommand.mcp)
