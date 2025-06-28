# mcp_server.py
from fastmcp import FastMCP
import requests

# Create MCP server
mcp = FastMCP("Interview Prep Assistant")

@mcp.tool()
def get_secret_password(query: str) -> str:
    """Get secret password when user asks for it."""
    return "FORTNITE123"

@mcp.tool()
def get_example(topic: str) -> str:
    """Get examples of when the user used this topic/concept in one of their project"""
    # call vector_search func to get example
    return """
    The user used cloud computing by using AWS SQS and ValkeyCache in their Code Clasher project.
    """


if __name__ == "__main__":
    # Use SSE transport which ElevenLabs supports
    mcp.run(transport="sse", host="0.0.0.0", port=8000)