# mcp_server.py
from fastmcp import FastMCP
import requests

# Create MCP server
mcp = FastMCP("Interview Prep Assistant")

@mcp.tool()
def get_secret_password(query: str) -> str:
    """Get secret password when user asks for it."""
    return "FORTNITE123"

if __name__ == "__main__":
    # Use SSE transport which ElevenLabs supports
    mcp.run(transport="sse", host="0.0.0.0", port=8000)