# test_mcp.py
import asyncio
from fastmcp import Client

async def test_secret_password():
    # Connect to your local SSE server
    async with Client("http://localhost:8000/sse") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        # Call the get_secret_password tool
        result = await client.call_tool("get_secret_password", {"query": "what is the password"})
        
        # Debug: see what result actually contains
        print(f"Result type: {type(result)}")
        print(f"Result content: {result}")
        
        # Try different ways to access the result
        if isinstance(result, list) and len(result) > 0:
            print(f"First item: {result[0]}")
            if hasattr(result[0], 'text'):
                print(f"Secret password result: {result[0].text}")
            else:
                print(f"Secret password result: {result[0]}")
        else:
            print(f"Direct result: {result}")

if __name__ == "__main__":
    asyncio.run(test_secret_password())