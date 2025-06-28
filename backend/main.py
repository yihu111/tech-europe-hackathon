from fastapi import FastAPI, HTTPException
import requests
import os
from base64 import b64decode
from typing import List

from utils.parsers import detect_frameworks_by_language
from data.dependencies_data import LANGUAGE_DEPENDENCY_FILES
from core.config import GITHUB_TOKEN
from clients.supabase_client import supabase
from models.job import Job

app = FastAPI()

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

# --- Save a job ---
@app.post("/save-job")
def save_repo_job(job: Job):
    """
    Save a single job to Supabase 'savedJobs' table.
    """
    try:
        response = supabase.table("savedJobs").insert(job.dict()).execute()
        if response.error:
            raise HTTPException(status_code=500, detail=str(response.error))
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Get all saved jobs ---
@app.get("/saved-jobs", response_model=List[Job])
def get_saved_jobs():
    try:
        response = supabase.table("savedJobs").select("*").execute()
        if response.error:
            raise HTTPException(status_code=500, detail=str(response.error))
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    