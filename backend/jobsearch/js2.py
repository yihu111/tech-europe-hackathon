import asyncio
import os
import json
from pathlib import Path
from typing import Dict, Any, List
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState
from langchain_openai import ChatOpenAI
from langchain_core.messages import convert_to_messages, AIMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from job_search_agent_prompt import (
    supervisor_prompt,
    job_analyzer_prompt,
    job_searcher_prompt
)

load_dotenv()

MODEL = "gpt-4o"
PROVIDER = "openai"


class JobListing(BaseModel):
    """Individual job listing"""
    title: str
    company: str
    location: str
    url: str
    tech_stack: List[str]
    posted_date: str = ""
    salary_range: str = ""
    description_snippet: str = ""


class JobSearchResult(BaseModel):
    """Final result with all job listings"""
    search_criteria: Dict[str, Any]
    total_jobs_found: int
    job_listings: List[JobListing]
    search_date: str


# Create Tavily search tool
def create_tavily_tool():
    """Create Tavily search tool for job searching"""
    return TavilySearch(
        max_results=5,
        search_depth="basic",
        include_answer=False,
        include_raw_content=False,
        include_images=False,
    )


# Helper to read user parameters from list.txt
def read_search_config() -> str:
   """Read raw search parameters from job_search_overview_w-foster.txt"""
   config_path = Path(__file__).parent.parent / "job_search_overview_w-foster.txt"
   if not config_path.exists():
       raise FileNotFoundError(f"Search configuration file not found: {config_path}")
   return config_path.read_text().strip()


# Create the specialized agents
async def create_job_agents():
    """Create all job search agents"""
    # Job searcher with Tavily
    job_searcher = create_react_agent(
        model=ChatOpenAI(model=MODEL),
        tools=[create_tavily_tool()],
        name="job_searcher",
        prompt=job_searcher_prompt
    )
    
    # Job analyzer (no tools needed)
    job_analyzer = create_react_agent(
        model=ChatOpenAI(model=MODEL),
        tools=[],
        name="job_analyzer",
        prompt=job_analyzer_prompt
    )
    
    return job_searcher, job_analyzer


async def create_job_search_supervisor():
    """Create the job search supervisor"""
    job_searcher, job_analyzer = await create_job_agents()
    job_supervisor = create_supervisor(
        agents=[job_searcher, job_analyzer],
        model=ChatOpenAI(model=MODEL),
        prompt=supervisor_prompt,
        output_mode="last_message",
    ).compile()
    return job_supervisor


def extract_jobs_from_result(result):
    """
    Extract job listings from supervisor result
    """
    if "messages" in result:
        # Get the last message from job_analyzer
        for message in reversed(result["messages"]):
            if hasattr(message, 'content') and message.content:
                try:
                    # Try to parse as JSON
                    content = message.content.strip()
                    if content.startswith('[') and content.endswith(']'):
                        return json.loads(content)
                    elif content.startswith('{') and content.endswith('}'):
                        # Single object, wrap in array
                        return [json.loads(content)]
                except json.JSONDecodeError:
                    continue
                    
            # Also check for tool calls that might contain the data
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    if 'args' in tool_call and 'formatted_jobs' in tool_call['args']:
                        return tool_call['args']['formatted_jobs']
    
    return []


def pretty_print_message(message, indent=False):
    """Pretty print a single message"""
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return
    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented)


def pretty_print_messages(update, last_message=False):
    """Pretty print message updates from the graph"""
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        if len(ns) == 0:
            return
        graph_id = ns[-1].split(":")[0]
        print(f"Update from subgraph {graph_id}:")
        print("\n")
        is_subgraph = True
    
    for node_name, node_update in update.items():
        update_label = f"Update from node {node_name}:"
        if is_subgraph:
            update_label = "\t" + update_label
        print(update_label)
        print("\n")
        
        if "messages" in node_update:
            messages = convert_to_messages(node_update["messages"])
            if last_message:
                messages = messages[-1:]
            for m in messages:
                pretty_print_message(m, indent=is_subgraph)
        else:
            print(f"Other update: {node_update}")
        print("\n")


async def search_tech_jobs():
    """
    Main function to search for tech jobs based on parameters in list.txt
    Returns structured list of job dictionaries
    """
    # Read user-defined search parameters
    config_text = read_search_config()
    print(f"\n🔍 Starting job search with parameters:\n{config_text}\n")
    
    supervisor = await create_job_search_supervisor()
    initial_state = {
        "messages": [{
            "role": "user", 
            "content": config_text
        }]
    }
    
    # Use invoke() to get final result
    result = await supervisor.ainvoke(initial_state)
    
    print("\n✅ Job Search Complete!\n")
    
    # Extract structured job data
    jobs = extract_jobs_from_result(result)
    
    return jobs


async def search_tech_jobs_with_streaming():
    """
    Alternative function that shows streaming but also returns structured result
    """
    config_text = read_search_config()
    print(f"\n🔍 Starting job search with parameters:\n{config_text}\n")
    
    supervisor = await create_job_search_supervisor()
    initial_state = {
        "messages": [{
            "role": "user", 
            "content": config_text
        }]
    }
    
    # Stream first for visibility
    final_result = None
    async for chunk in supervisor.astream(initial_state, stream_mode="updates", subgraphs=True):
        pretty_print_messages(chunk)
        # Capture the final result when we see __end__
        if "__end__" in chunk:
            final_result = chunk["__end__"]
    
    # If we didn't get it from streaming, invoke directly
    if not final_result:
        final_result = await supervisor.ainvoke(initial_state)
    
    jobs = extract_jobs_from_result(final_result)
    
    print("\n✅ Job Search Complete!\n")
    return jobs


# Example usage
async def test_job_search():
    """Test the job search and return structured results"""
    jobs = await search_tech_jobs()
    
    # Print the structured output
    print("Found jobs:")
    print(f"Total: {len(jobs)} jobs\n")
    
    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job.get('title', 'Unknown Title')}")
        print(f"   URL: {job.get('url', 'No URL')}")
        print(f"   Skills: {job.get('required_skills', [])}")
        print(f"   Fit Score: {job.get('fit_score', 0)}%")
        print(f"   Missing Skills: {job.get('missing_skills', [])}")
        print()
    
    return jobs


async def test_job_search_with_streaming():
    """Test with streaming output plus final structured result"""
    jobs = await search_tech_jobs_with_streaming()
    
    # Print the structured output
    print("\n" + "="*50)
    print("FINAL STRUCTURED RESULTS:")
    print("="*50)
    
    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job.get('title', 'Unknown Title')}")
        print(f"   URL: {job.get('url', 'No URL')}")
        print(f"   Skills: {job.get('required_skills', [])}")
        print(f"   Fit Score: {job.get('fit_score', 0)}%")
        print(f"   Missing Skills: {job.get('missing_skills', [])}")
        print()
    
    return jobs


def run_job_search():
    """Synchronous wrapper to run the job search"""
    return asyncio.run(test_job_search())


def run_job_search_with_streaming():
    """Synchronous wrapper to run job search with streaming"""
    return asyncio.run(test_job_search_with_streaming())


if __name__ == "__main__":    
    # Choose which version to run:
    
    # Option 1: Clean structured output only
    jobs = asyncio.run(test_job_search())
    print("THE JOBS ARE HERE:")
    print(jobs)
    
    # Option 2: Streaming + structured output (uncomment to use)
    # jobs = asyncio.run(test_job_search_with_streaming())
    
    # Option 3: Just get jobs without printing (uncomment to use)
    # jobs = asyncio.run(search_tech_jobs())
    # print(f"Found {len(jobs)} jobs")