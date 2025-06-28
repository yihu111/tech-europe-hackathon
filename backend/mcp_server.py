# mcp_server.py
from fastmcp import FastMCP
import requests
from vector_search import search_across_all_relevant_collections

# Create MCP server
mcp = FastMCP("Interview Prep Assistant")

@mcp.tool()
def get_secret_password(query: str) -> str:
    """Get secret password when user asks for it."""
    return "FORTNITE123"

# mcp_server.py
from fastmcp import FastMCP
import requests
from vector_search import search_across_all_relevant_collections

# Create MCP server
mcp = FastMCP("Interview Prep Assistant")


@mcp.tool()
def get_secret_password(query: str) -> str:
    """Get secret password when user asks for it."""
    return "FORTNITE123"



@mcp.tool()
def get_example(topic: str) -> str:
    """Get examples of when the user used this topic/concept in one of their project"""
    try:
        # Call vector_search func to get examples
        examples = search_across_all_relevant_collections(
            interview_question=topic,
            k_per_collection=5,
            score_threshold=0.5
        )
        
        # Return first example if available
        if examples and len(examples) > 0:
            return examples[0]
        else:
            return f"No examples found for topic: {topic}"
            
    except Exception as e:
        return f"Error retrieving examples: {str(e)}"



if __name__ == "__main__":
    # Use SSE transport which ElevenLabs supports
    mcp.run(transport="sse", host="0.0.0.0", port=8000)