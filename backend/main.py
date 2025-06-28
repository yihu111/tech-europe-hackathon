from fastapi import FastAPI, HTTPException
import requests

app = FastAPI()

GITHUB_API = "https://api.github.com"

@app.get("/repos/{username}")
def get_repos_and_languages(username: str):
    # Fetch repositories
    repos_url = f"{GITHUB_API}/users/{username}/repos"
    repos_response = requests.get(repos_url)

    if repos_response.status_code != 200:
        raise HTTPException(status_code=repos_response.status_code, detail="Failed to fetch repos")

    repos = repos_response.json()

    result = []

    for repo in repos:
        repo_name = repo["name"]
        languages_url = f"{GITHUB_API}/repos/{username}/{repo_name}/languages"
        languages_response = requests.get(languages_url)

        if languages_response.status_code != 200:
            languages = {}
        else:
            languages = languages_response.json()

        result.append({
            "repo_name": repo_name,
            "repo_url": repo["html_url"],
            "languages": languages
        })

    return result
