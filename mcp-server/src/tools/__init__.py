from fastmcp import FastMCP

from .customers_tools import Command, Queries
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
mcp.mount(OrchestratorQuery.mcp)