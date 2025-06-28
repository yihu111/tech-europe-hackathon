from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
import os
from base64 import b64decode
from typing import List
import json
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

from vector_search import (
    list_available_collections, 
    search_user_contributions, 
    VectorSearchResponse
)

from utils.parsers import detect_frameworks_by_language
from data.dependencies_data import LANGUAGE_DEPENDENCY_FILES
from core.config import GITHUB_TOKEN
from models.job import Job

from jobsearch.job_search_agent import search_tech_jobs
from jobsearch.job_search import run_job_search

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to your frontend origin, e.g. ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods including OPTIONS, POST, GET, etc.
    allow_headers=["*"],
)

GITHUB_API = "https://api.github.com"
headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def get_all_files(username: str, repo_name: str):
    """
    Get list of all file paths in the repo (recursive).
    """
    url = f"{GITHUB_API}/repos/{username}/{repo_name}/git/trees/HEAD?recursive=1"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []
    data = response.json()
    return [item['path'] for item in data.get('tree', []) if item['type'] == 'blob']

@app.get("/repos/{username}")
def get_repos_and_data(username: str):
    repos_url = f"{GITHUB_API}/users/{username}/repos?per_page=100"
    repos_response = requests.get(repos_url, headers=headers)

    if repos_response.status_code != 200:
        raise HTTPException(status_code=repos_response.status_code, detail="Failed to fetch repos")

    repos = repos_response.json()
    result = []

    for repo in repos:
        repo_name = repo["name"]
        repo_url = repo["html_url"]

        lang_url = f"{GITHUB_API}/repos/{username}/{repo_name}/languages"
        lang_response = requests.get(lang_url, headers=headers)
        languages = lang_response.json() if lang_response.status_code == 200 else {}

        all_dependencies = []
        files = get_all_files(username, repo_name)

        for lang in languages.keys():
            lang_lower = lang.lower()
            if lang_lower in LANGUAGE_DEPENDENCY_FILES:
                for filename, parser in LANGUAGE_DEPENDENCY_FILES[lang_lower]:
                    matching_files = [f for f in files if f.endswith(filename)]
                    for file_path in matching_files:
                        file_url = f"{GITHUB_API}/repos/{username}/{repo_name}/contents/{file_path}"
                        file_response = requests.get(file_url, headers=headers)

                        if file_response.status_code == 200:
                            content = file_response.json().get("content")
                            if content:
                                try:
                                    decoded = b64decode(content).decode("utf-8")
                                    deps = parser(decoded)
                                    all_dependencies.extend(deps)
                                except Exception as e:
                                    print(f"Failed to decode or parse {file_path} in {repo_name}: {e}")

        frameworks = detect_frameworks_by_language(languages, all_dependencies)

        result.append({
            "repo_name": repo_name,
            "repo_url": repo_url,
            "languages": languages,
            "frameworks": frameworks,
        })

    return result

from collections import defaultdict


def get_aggregated_repo_data(username: str):
    repos_data = get_repos_and_data(username)  # your existing function
    
    combined_languages = defaultdict(int)
    combined_frameworks = defaultdict(int)

    for repo in repos_data:
        # Merge languages (sum values if numeric)
        for lang, value in repo.get("languages", {}).items():
            # Assuming value is lines of code or similar metric
            combined_languages[lang] += value
        
        # Combine frameworks (count occurrences)
        for fw in repo.get("frameworks", []):
            combined_frameworks[fw] += 1
    
    # Convert defaultdicts back to normal dict or list
    combined_languages = dict(combined_languages)
    combined_frameworks = list(combined_frameworks.keys())  # Or keep dict if you want counts
    
    return {
        "languages": combined_languages,
        "frameworks": combined_frameworks,
    }





# =======================


from pydantic import BaseModel

class SearchRequest(BaseModel):
   username: str



from knowledge_pipeline import analyze_github_user

@app.post("/overview")
async def overview(request: SearchRequest):
    """
    Analyze GitHub user's repos and extract knowledge for job search.
    """
    try:
        # Call your knowledge pipeline with the username
        # result = await analyze_github_user(request.username)
        result = get_aggregated_repo_data(request.username)
        print(result)
        return {
            "status": "success",
            "username": request.username,
            "message": "Knowledge extraction completed",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
   


#from jobsearch.job_search_agent import run_job_search

@app.post("/jobsearch")
async def jobSearch(request: SearchRequest):
    """
    Run job search using stored tech stack keywords.
    """
    try:
        # Call your job search function - returns list of dicts with "description" and "url"
        jobs = await run_job_search(request.languages, request.frameworks)
        # [{"description": <job desc>, "url": <job page url}, {"description": <job desc>, "url": <job page url}. {"description": <job desc>, "url": <job page url},]
        
        return jobs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    



@app.post("/start-job-search")
async def start_job_search():
   """
   Start job search using stored tech stack keywords.
   """
   try:
       tech_stack_file_path = "user_tech_stack.json"  # Path to the stored keywords
       
       # Call your job search function with file path
       jobs = await search_tech_jobs(
           tech_stack_file_path=tech_stack_file_path,
           location="remote",
           experience_level="senior"
       )
       
       return {
           "status": "success",
           "jobs": jobs
       }
       
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))








# Pydantic models for vector search requests
class SearchRequest(BaseModel):
    question: str
    collection_name: Optional[str] = None
    max_results: int = 10

class SearchAllRequest(BaseModel):
    question: str
    max_results_per_collection: int = 5

# Vector Search Endpoints
@app.get("/collections")
def get_collections():
    """Get all available ChromaDB collections"""
    collections = list_available_collections()
    collection_info = []
    
    for collection_name in collections:
        info = get_collection_info(collection_name)
        if info:
            collection_info.append(info)
    
    return {
        "collections": collections,
        "collection_details": collection_info,
        "total_collections": len(collections)
    }

@app.post("/search", response_model=VectorSearchResponse)
def search_contributions(request: SearchRequest):
    """
    Search for relevant user contributions based on an interview question.
    If no collection_name is provided, searches the first available collection.
    """
    if not request.collection_name:
        # Get first available collection
        collections = list_available_collections()
        if not collections:
            raise HTTPException(status_code=404, detail="No ChromaDB collections found")
        request.collection_name = collections[0]
    
    # Verify collection exists
    collections = list_available_collections()
    if request.collection_name not in collections:
        raise HTTPException(
            status_code=404, 
            detail=f"Collection '{request.collection_name}' not found. Available: {collections}"
        )
    
    try:
        result = search_user_contributions(
            interview_question=request.question,
            collection_name=request.collection_name,
            k=request.max_results
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/search/all")
def search_all_contributions(request: SearchAllRequest):
    """
    Search across all available collections for relevant contributions.
    Returns results grouped by collection.
    """
    try:
        results = search_across_all_collections(
            interview_question=request.question,
            k_per_collection=request.max_results_per_collection
        )
        
        if not results:
            raise HTTPException(status_code=404, detail="No results found in any collection")
        
        return {
            "query": request.question,
            "results_by_collection": results,
            "total_collections_searched": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/collections/{collection_name}/info")
def get_collection_details(collection_name: str):
    """Get detailed information about a specific collection"""
    collections = list_available_collections()
    if collection_name not in collections:
        raise HTTPException(
            status_code=404, 
            detail=f"Collection '{collection_name}' not found. Available: {collections}"
        )
    
    info = get_collection_info(collection_name)
    if not info:
        raise HTTPException(status_code=500, detail="Failed to get collection information")
    
    return info
