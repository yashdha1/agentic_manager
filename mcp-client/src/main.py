from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import router as api_router
from src.core.logger import logger
from src.core.tracing import configure_langsmith_tracing
from src.declarative.AgentSpec import _all_tools
from src.declarative.mcp_tools import prepare_workflow


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_langsmith_tracing()
    logger.info("Starting up — connecting to MCP server...")
    await prepare_workflow() 
    logger.info(f"MCP client is ready to serve requests. {len(_all_tools)} tools loaded.")
    yield
    logger.info("Shutting down the MCP client...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Hello from the client"}