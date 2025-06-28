import asyncio
import os
from typing import Dict, Any, List
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState
from langchain_openai import ChatOpenAI
from langchain_core.messages import convert_to_messages
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv
from job_search_agent_prompt import supervisor_prompt, job_analyzer_prompt, job_searcher_prompt, result_formatter_prompt

load_dotenv()
os.getenv("TAVILY_API_KEY")
os.getenv("OPENAI_API_KEY")

MODEL = "gpt-4o-mini"
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
    # You'll need to set TAVILY_API_KEY environment variable
    return TavilySearchResults(
        max_results=10,
        search_depth="advanced",
        include_answer=False,
        include_raw_content=True,
        include_images=False,
    )


# Mock send results tool
@tool
def send_results(formatted_jobs: str) -> str:
    """Send the formatted job search results"""
    print("\n📋 JOB SEARCH RESULTS:")
    print("=" * 50)
    print(formatted_jobs)
    print("=" * 50)
    return "✅ Job search results delivered successfully"


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
    
    # Result formatter (no tools needed)
    result_formatter = create_react_agent(
        model=ChatOpenAI(model=MODEL),
        tools=[],
        name="result_formatter",
        prompt=result_formatter_prompt
    )
    
    return job_searcher, job_analyzer, result_formatter


async def create_job_search_supervisor():
    """Create the job search supervisor"""
    
    job_searcher, job_analyzer, result_formatter = await create_job_agents()
    
    job_supervisor = create_supervisor(
        agents=[job_searcher, job_analyzer, result_formatter],
        tools=[send_results],
        model=ChatOpenAI(model=MODEL),
        prompt=supervisor_prompt,
        add_handoff_back_messages=True,
        output_mode="last_message",
    ).compile()
    
    return job_supervisor


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


async def search_tech_jobs(tech_stack: List[str], 
                          location: str = "remote", 
                          experience_level: str = "mid-level"):
    """
    Main function to search for tech jobs
    
    Args:
        tech_stack: List of technologies (e.g., ["Python", "Django", "PostgreSQL"])
        location: Job location preference (e.g., "remote", "San Francisco", "hybrid")
        experience_level: Level of position (e.g., "junior", "mid-level", "senior")
    """
    
    supervisor = await create_job_search_supervisor()
    
    # Create search query from parameters
    tech_string = ", ".join(tech_stack)
    search_query = f"""
    Find 10 {experience_level} tech job listings for developers with these skills:
    - Tech Stack: {tech_string}
    - Location: {location}
    
    Requirements:
    1. Find ACTUAL job postings with direct application links
    2. Jobs should require most of the specified technologies
    3. Include a mix of companies (startups, mid-size, enterprise)
    4. Prioritize recent postings (last 30 days)
    5. Include salary information when available
    """
    
    initial_state = {
        "messages": [{
            "role": "user", 
            "content": search_query
        }]
    }
    
    print(f"\n🔍 Starting job search for {tech_string} positions...\n")
    
    async for chunk in supervisor.astream(initial_state, stream_mode="updates", subgraphs=True):
        pretty_print_messages(chunk)
    
    print("\n✅ Job Search Complete!\n")


# Example usage
async def test_job_search():
    """Test the job search with sample parameters"""
    
    # Example 1: Python Backend Developer
    await search_tech_jobs(
        tech_stack=["Python", "Django", "PostgreSQL", "Redis", "Docker"],
        location="remote",
        experience_level="senior"
    )



if __name__ == "__main__":    
    asyncio.run(test_job_search())