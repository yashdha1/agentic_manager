from fastmcp import FastMCP

mcp = FastMCP("e_commerce_mcp")


@mcp.tool
def greet(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"
