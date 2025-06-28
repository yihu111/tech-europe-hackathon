import asyncio
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Union
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import convert_to_messages
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

# Load environment variables
load_dotenv()

MODEL = "o4-mini"
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
    """Returns a configured TavilySearch tool"""
    return TavilySearch(
        max_results=5,
        search_depth="basic",
        include_answer=False,
        include_raw_content=False,
        include_images=False,
    )

@tool
def send_results(formatted_jobs: str) -> str:
    """Receive formatted JSON string of job listings"""
    # Simply return the JSON string for supervisor to output
    return formatted_jobs

# Helper to read user parameters from list.txt
def read_search_config() -> str:
    """Read raw search parameters from list.txt"""
    config_path = Path(__file__).parent / "list.txt"
    if not config_path.exists():
        raise FileNotFoundError(f"Search configuration file not found: {config_path}")
    return config_path.read_text().strip()

# Create specialized agents
async def create_job_agents():
    """Instantiate job_searcher and job_analyzer agents"""
    job_searcher = create_react_agent(
        model=ChatOpenAI(model=MODEL),
        tools=[create_tavily_tool()],
        name="job_searcher",
        prompt=job_searcher_prompt
    )
    job_analyzer = create_react_agent(
        model=ChatOpenAI(model=MODEL),
        tools=[],
        name="job_analyzer",
        prompt=job_analyzer_prompt
    )
    return job_searcher, job_analyzer

async def create_job_search_supervisor():
    """Set up the supervisor coordinating the pipeline"""
    job_searcher, job_analyzer = await create_job_agents()
    return create_supervisor(
        agents=[job_searcher, job_analyzer],
        tools=[send_results],
        model=ChatOpenAI(model=MODEL),
        prompt=supervisor_prompt,
        add_handoff_back_messages=False,
        output_mode="last_message",
    ).compile()

async def search_tech_jobs() -> Union[List[Dict[str, Any]], None]:
    """Main function to search for tech jobs and return JSON results"""
    try:
        config_text = read_search_config()
    except Exception as e:
        print(f"Error reading config: {e}")
        return None

    print(f"\n🔍 Starting job search with parameters:\n{config_text}\n")
    supervisor = await create_job_search_supervisor()
    initial_state = {"messages": [{"role": "user", "content": config_text}]}

    # Get final result via a single invocation
    try:
        result = await supervisor.ainvoke(initial_state)
    except Exception as e:
        print(f"Error during job search: {e}")
        return None

    # result may be a JSON string or already a dict/list
    if isinstance(result, (dict, list)):
        jobs = result
    else:
        try:
            jobs = json.loads(result)
        except Exception:
            print("Error: Received invalid JSON from supervisor:")
            print(result)
            return None

    # Pretty-print output
    print(json.dumps(jobs, indent=2))
    return jobs

# CLI entry point
def main():
    """Run the job search when executed as a script"""
    asyncio.run(search_tech_jobs())

if __name__ == "__main__":
    main()
