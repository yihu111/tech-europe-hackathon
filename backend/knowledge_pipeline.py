import operator
import os
import ast
import hashlib
import requests
import base64
from typing import Annotated, List, Dict, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from collections import Counter
from uuid import uuid4

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.types import Send
from langgraph.graph import StateGraph, START, END
from langchain_chroma import Chroma
from langchain_core.documents import Document

MODEL = "gpt-4o-mini"
llm = ChatOpenAI(model=MODEL)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Chroma setup - LangChain way
CHROMA_DB_PATH = "./chroma_langchain_db"

# GitHub API setup
GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


# Pydantic models for structured output
class FileAnalysis(BaseModel):
    frameworks: List[str] = Field(description="List of frameworks/libraries detected")
    concepts: List[str] = Field(description="Key concepts, patterns, or functionality")
    architecture_patterns: List[str] = Field(
        description="Design patterns or architectural concepts"
    )
    file_purpose: str = Field(description="What this file does in 1-2 sentences")


class ConceptSummary(BaseModel):
    top_frameworks: List[Dict[str, int]] = Field(
        description="Most used frameworks with counts"
    )
    key_concepts: List[Dict[str, int]] = Field(
        description="Important concepts with frequency"
    )
    architecture_overview: str = Field(
        description="Overall project architecture summary"
    )
    tech_stack: List[str] = Field(description="Main technologies used")


# Overall repo analysis state
class RepoAnalysisState(TypedDict):
    username: str
    repo_name: str
    repo_files: List[Dict]
    file_analyses: Annotated[List[Dict], operator.add]
    final_summary: Optional[ConceptSummary]
    chroma_collection: Optional[str]
    stored_documents: int
    job_search_file: Optional[str]


# Individual file analysis state (sent to each analyze_file_node)
class FileState(TypedDict):
    username: str
    repo_name: str
    file_path: str
    file_content: str
    file_type: str


# NODE FUNCTIONS


def get_repo_files(username: str, repo_name: str) -> List[Dict]:
    """Get all files from GitHub repo using API"""
    url = f"{GITHUB_API}/repos/{username}/{repo_name}/git/trees/HEAD?recursive=1"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch repo files: {response.status_code}")
        return []

    data = response.json()
    files = []

    # File extensions we care about
    relevant_extensions = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".dart",
        ".vue",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
    }

    # Directories to ignore
    ignore_patterns = [
        "node_modules/",
        ".git/",
        "__pycache__/",
        ".venv/",
        "venv/",
        "env/",
        "build/",
        "dist/",
        ".next/",
        "target/",
        "vendor/",
        ".pytest_cache/",
    ]

    for item in data.get("tree", []):
        if item["type"] == "blob":  # It's a file
            file_path = item["path"]

            # Skip ignored directories
            if any(ignore in file_path for ignore in ignore_patterns):
                continue

            # Check if it's a relevant file type
            if any(file_path.endswith(ext) for ext in relevant_extensions):
                files.append(
                    {"path": file_path, "url": item["url"], "size": item.get("size", 0)}
                )

    return files


def get_file_content(username: str, repo_name: str, file_path: str) -> str:
    """Get content of a specific file from GitHub"""
    url = f"{GITHUB_API}/repos/{username}/{repo_name}/contents/{file_path}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch file {file_path}: {response.status_code}")
        return ""

    data = response.json()
    content = data.get("content", "")

    if content:
        try:
            # Decode base64 content
            decoded = base64.b64decode(content).decode("utf-8")
            return decoded
        except Exception as e:
            print(f"Failed to decode {file_path}: {e}")
            return ""

    return ""


def select_repos_to_analyze(username: str, max_repos: int = 10) -> List[str]:
    """Select up to max_repos most interesting repos from user's repositories"""
    url = f"{GITHUB_API}/users/{username}/repos?per_page=100&sort=updated"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch repos for {username}: {response.status_code}")

    repos = response.json()

    # Filter and score repos
    scored_repos = []
    for repo in repos:
        # Skip forks and very small repos
        if repo["fork"] or repo["size"] < 10:
            continue

        # Score based on activity and size
        score = (
            repo["stargazers_count"] * 2
            + repo["forks_count"] * 3
            + repo["size"]
            + (100 if not repo["archived"] else 0)
        )

        scored_repos.append((repo["name"], score, repo))

    if not scored_repos:
        # Fallback to first non-fork repos
        fallback_repos = []
        for repo in repos:
            if not repo["fork"]:
                fallback_repos.append(repo["name"])
                if len(fallback_repos) >= max_repos:
                    break
        
        if not fallback_repos:
            raise Exception(f"No suitable repos found for {username}")
        
        print(f"Using fallback repos: {fallback_repos}")
        return fallback_repos

    # Return the top scored repos (up to max_repos)
    scored_repos.sort(key=lambda x: x[1], reverse=True)
    selected_repos = [repo[0] for repo in scored_repos[:max_repos]]
    
    print(f"Selected {len(selected_repos)} repos for analysis:")
    for i, (name, score, _) in enumerate(scored_repos[:max_repos]):
        print(f"  {i+1}. {name} (score: {score})")
    
    return selected_repos


def discover_files(state: RepoAnalysisState) -> RepoAnalysisState:
    """Find all relevant code files in the GitHub repo"""
    username = state["username"]
    repo_name = state["repo_name"]

    files = get_repo_files(username, repo_name)
    print(f"Found {len(files)} files to analyze in {username}/{repo_name}")

    return {**state, "repo_files": files}


def static_analysis(file_path: str, content: str) -> Dict:
    """Quick static analysis to extract imports and basic info"""
    file_ext = os.path.splitext(file_path)[1]
    frameworks = []

    if file_ext == ".py":
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        frameworks.append(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        frameworks.append(node.module.split(".")[0])
        except:
            pass

    elif file_ext in [".js", ".ts", ".tsx", ".jsx"]:
        # Simple regex-based import extraction
        import re

        import_patterns = [
            r"import.*from ['\"]([^'\"]+)['\"]",
            r"require\(['\"]([^'\"]+)['\"]\)",
            r"import ['\"]([^'\"]+)['\"]",
        ]
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            frameworks.extend(
                [m.split("/")[0] for m in matches if not m.startswith(".")]
            )

    return {"static_frameworks": list(set(frameworks))}


async def analyze_file_node(state: FileState) -> Dict:
    """LLM-powered analysis of a single file"""
    file_path = state["file_path"]
    file_content = state["file_content"]
    file_type = state["file_type"]

    # Get static analysis first
    static_info = static_analysis(file_path, file_content)

    # Truncate content if too long
    max_content_length = 4000
    if len(file_content) > max_content_length:
        file_content = file_content[:max_content_length] + "\n... [truncated]"

    analysis_prompt = f"""
    Analyze this {file_type} file and extract key information:
    
    File: {os.path.basename(file_path)}
    Content:
    ```
    {file_content}
    ```
    
    Static analysis found these imports: {static_info.get('static_frameworks', [])}
    
    Please provide a structured analysis focusing on:
    1. Frameworks/libraries used (expand on the static analysis)
    2. Key concepts, functionality, or business logic
    3. Architecture patterns (MVC, Observer, Factory, etc.)
    4. What this file's purpose is
    
    Be concise but specific. Focus on technical concepts that would be relevant for job interviews.
    """

    try:
        response = await llm.with_structured_output(FileAnalysis).ainvoke(
            analysis_prompt
        )

        return {
            "file_analyses": [
                {
                    "file_path": file_path,
                    "file_type": file_type,
                    "analysis": response.model_dump(),
                    "static_frameworks": static_info.get("static_frameworks", []),
                }
            ]
        }
    except Exception as e:
        print(f"Analysis failed for {file_path}: {e}")
        return {
            "file_analyses": [
                {
                    "file_path": file_path,
                    "file_type": file_type,
                    "analysis": {
                        "frameworks": static_info.get("static_frameworks", []),
                        "concepts": [],
                        "architecture_patterns": [],
                        "file_purpose": f"Failed to analyze: {str(e)}",
                    },
                    "static_frameworks": static_info.get("static_frameworks", []),
                }
            ]
        }


async def summarize_analysis(state: RepoAnalysisState) -> RepoAnalysisState:
    """Reduce step - combine all file analyses into final summary"""
    file_analyses = state["file_analyses"]

    # Collect all frameworks and concepts
    all_frameworks = []
    all_concepts = []
    all_patterns = []
    file_purposes = []

    for analysis in file_analyses:
        if "analysis" in analysis:
            all_frameworks.extend(analysis["analysis"].get("frameworks", []))
            all_concepts.extend(analysis["analysis"].get("concepts", []))
            all_patterns.extend(analysis["analysis"].get("architecture_patterns", []))
            file_purposes.append(analysis["analysis"].get("file_purpose", ""))
        all_frameworks.extend(analysis.get("static_frameworks", []))

    # Count frequencies
    framework_counts = Counter(all_frameworks)
    concept_counts = Counter(all_concepts)
    pattern_counts = Counter(all_patterns)

    # Create summary using LLM
    summary_prompt = f"""
    Based on the analysis of {len(file_analyses)} files, create a comprehensive project summary:
    
    Most used frameworks: {dict(framework_counts.most_common(10))}
    Key concepts found: {dict(concept_counts.most_common(15))}
    Architecture patterns: {dict(pattern_counts.most_common(5))}
    
    Sample file purposes:
    {chr(10).join(file_purposes[:10])}
    
    Provide:
    1. Top frameworks with their usage counts
    2. Key concepts with frequency 
    3. Overall architecture description
    4. Main tech stack summary
    """

    try:
        summary = await llm.with_structured_output(ConceptSummary).ainvoke(
            summary_prompt
        )

        return {**state, "final_summary": summary.dict()}
    except Exception as e:
        # Fallback summary
        return {
            **state,
            "final_summary": {
                "top_frameworks": [
                    {"name": k, "count": v} for k, v in framework_counts.most_common(10)
                ],
                "key_concepts": [
                    {"concept": k, "count": v}
                    for k, v in concept_counts.most_common(15)
                ],
                "architecture_overview": f"Analysis of {len(file_analyses)} files completed with some errors",
                "tech_stack": list(framework_counts.keys())[:10],
            },
        }


async def store_in_chroma(state: RepoAnalysisState) -> RepoAnalysisState:
    """Store all analysis results in Chroma using LangChain integration"""

    username = state["username"]
    repo_name = state["repo_name"]
    final_summary = state["final_summary"]
    file_analyses = state["file_analyses"]

    # Create collection name from repo info
    collection_name = f"repo_{username}_{repo_name}_{hashlib.md5(f'{username}/{repo_name}'.encode()).hexdigest()[:8]}"

    print(f"Storing in Chroma collection: {collection_name}")

    try:
        # Create Chroma vector store with LangChain
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH,
        )

        # Prepare LangChain Documents
        documents = []
        document_ids = []

        # 1. Store project-level summary
        if final_summary:
            summary_text = f"""
            Project: {username}/{repo_name}
            Tech Stack: {', '.join(final_summary.get('tech_stack', []))}
            Architecture: {final_summary.get('architecture_overview', '')}
            Top Frameworks: {', '.join([fw.get('name', str(fw)) for fw in final_summary.get('top_frameworks', [])[:5]])}
            Key Concepts: {', '.join([c.get('concept', str(c)) for c in final_summary.get('key_concepts', [])[:10]])}
            """

            summary_doc = Document(
                page_content=summary_text.strip(),
                metadata={
                    "type": "project_summary",
                    "repo_name": repo_name,
                    "username": username,
                    "level": "project",
                },
            )

            documents.append(summary_doc)
            document_ids.append(f"{collection_name}_summary")

        # 2. Store individual file analyses
        for i, analysis in enumerate(file_analyses):
            if "analysis" in analysis:
                file_path = analysis["file_path"]
                file_analysis = analysis["analysis"]

                # Create rich document text
                file_doc_text = f"""
                File: {file_path}
                Repository: {username}/{repo_name}
                Purpose: {file_analysis.get('file_purpose', '')}
                Frameworks: {', '.join(file_analysis.get('frameworks', []))}
                Concepts: {', '.join(file_analysis.get('concepts', []))}
                Architecture Patterns: {', '.join(file_analysis.get('architecture_patterns', []))}
                File Type: {analysis.get('file_type', '')}
                """

                file_doc = Document(
                    page_content=file_doc_text.strip(),
                    metadata={
                        "type": "file_analysis",
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "file_type": analysis.get("file_type", ""),
                        "repo_name": repo_name,
                        "username": username,
                        "level": "file",
                        # Convert lists to strings for Chroma compatibility
                        "frameworks": ", ".join(file_analysis.get("frameworks", [])),
                        "concepts": ", ".join(file_analysis.get("concepts", [])),
                    },
                )

                documents.append(file_doc)
                document_ids.append(f"{collection_name}_file_{i}")

        # 3. Store concept-level documents for better retrieval
        if final_summary:
            for j, concept in enumerate(final_summary.get("key_concepts", [])):
                concept_name = concept.get("concept", str(concept))
                concept_count = concept.get("count", 1)

                concept_doc_text = f"""
                Concept: {concept_name}
                Repository: {username}/{repo_name}
                Used in {concept_count} files across the {repo_name} project.
                This concept is part of the project's core functionality and technical implementation.
                """

                concept_doc = Document(
                    page_content=concept_doc_text.strip(),
                    metadata={
                        "type": "concept",
                        "concept": concept_name,
                        "frequency": concept_count,
                        "repo_name": repo_name,
                        "username": username,
                        "level": "concept",
                    },
                )

                documents.append(concept_doc)
                document_ids.append(f"{collection_name}_concept_{j}")

        # Store in Chroma using LangChain's add_documents
        if documents:
            vector_store.add_documents(documents=documents, ids=document_ids)

            print(f"✅ Stored {len(documents)} documents in Chroma")
            print(f"   - Project summary: 1")
            print(f"   - File analyses: {len(file_analyses)}")
            print(f"   - Concept documents: {len(documents) - len(file_analyses) - 1}")
            print(f"   - Collection: {collection_name}")
            print(f"   - Persist directory: {CHROMA_DB_PATH}")

        return {
            **state,
            "chroma_collection": collection_name,
            "stored_documents": len(documents),
        }

    except Exception as e:
        print(f"❌ Failed to store in Chroma: {e}")
        return {**state, "chroma_collection": None, "stored_documents": 0}


def save_job_search_overview(state: RepoAnalysisState) -> RepoAnalysisState:
    """Save a job search overview to text file for Tavily"""

    username = state["username"]
    repo_name = state["repo_name"]
    final_summary = state["final_summary"]
    file_analyses = state["file_analyses"]

    if not final_summary:
        print("No summary available to save")
        return state

    # Create job search description
    tech_stack = final_summary.get("tech_stack", [])[:8]  # Top 8 technologies
    top_frameworks = final_summary.get("top_frameworks", [])[:6]  # Top 6 frameworks
    key_concepts = final_summary.get("key_concepts", [])[:10]  # Top 10 concepts

    # Build experience context
    total_files = len(file_analyses)
    framework_experience = []
    for fw in top_frameworks:
        name = fw.get("name", str(fw))
        count = fw.get("count", 1)
        if count >= 5:
            exp_level = "extensive experience"
        elif count >= 3:
            exp_level = "solid experience"
        else:
            exp_level = "some experience"
        framework_experience.append(f"{name} ({exp_level})")

    # Create comprehensive job search overview
    overview = f"""Software Developer with expertise in {', '.join(tech_stack[:3])} looking for opportunities.

TECHNICAL SKILLS:
{', '.join(tech_stack)}

FRAMEWORK EXPERIENCE:
{', '.join(framework_experience)}

KEY CAPABILITIES:
{', '.join([c.get('concept', str(c)) for c in key_concepts[:6]])}

PROJECT BACKGROUND:
Analyzed repository: {username}/{repo_name} containing {total_files} files. 
Architecture: {final_summary.get('architecture_overview', 'Modern software architecture with focus on scalable solutions.')}

EXPERIENCE LEVEL:
Demonstrated practical experience across {len(tech_stack)} technologies with hands-on implementation in real projects.

IDEAL ROLES:
Software Engineer, Full Stack Developer, Backend Developer, Frontend Developer roles involving {', '.join(tech_stack[:4])}"""

    # Save to file
    filename = f"job_search_overview_{username}.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(overview)

        print(f"📄 Job search overview saved to: {filename}")

        return {**state, "job_search_file": filename}

    except Exception as e:
        print(f"❌ Failed to save job search overview: {e}")
        return {**state, "job_search_file": None}


# Mapping function for Send API
def continue_to_file_analysis(state: RepoAnalysisState):
    """Map discovered files to parallel analysis tasks"""
    username = state["username"]
    repo_name = state["repo_name"]
    repo_files = state["repo_files"]

    # Create Send objects for each file
    send_objects = []
    for file_info in repo_files:
        file_path = file_info["path"]

        # Skip very large files to avoid API limits
        if file_info.get("size", 0) > 100000:  # 100KB limit
            print(f"Skipping large file: {file_path}")
            continue

        # Get file content from GitHub
        content = get_file_content(username, repo_name, file_path)
        if not content:
            continue

        file_ext = os.path.splitext(file_path)[1]

        send_objects.append(
            Send(
                "analyze_file",
                {
                    "username": username,
                    "repo_name": repo_name,
                    "file_path": file_path,
                    "file_content": content,
                    "file_type": file_ext,
                },
            )
        )

    print(f"Sending {len(send_objects)} files for analysis")
    return send_objects


# Build the repo analysis graph
def create_repo_analysis_graph():
    """Create the repo analysis graph with map-reduce pattern"""

    graph = StateGraph(RepoAnalysisState)

    # Add nodes
    graph.add_node("discover_files", discover_files)
    graph.add_node(
        "analyze_file", analyze_file_node
    )  # Gets called multiple times via Send
    graph.add_node("summarize_analysis", summarize_analysis)
    graph.add_node("store_in_chroma", store_in_chroma)
    graph.add_node("save_job_search_overview", save_job_search_overview)

    # Add edges
    graph.add_edge(START, "discover_files")

    # Map step: Send each file to parallel analysis
    graph.add_conditional_edges(
        "discover_files", continue_to_file_analysis, ["analyze_file"]
    )

    # Reduce step: All analyze_file nodes flow to summary
    graph.add_edge("analyze_file", "summarize_analysis")
    graph.add_edge("summarize_analysis", "store_in_chroma")
    graph.add_edge("store_in_chroma", "save_job_search_overview")
    graph.add_edge("save_job_search_overview", END)

    return graph.compile()


# Main execution function
async def analyze_repo(repo_path: str):
    """Run the complete repo analysis"""

    graph = create_repo_analysis_graph()

    # Save visualization
    graph.get_graph(xray=True).draw_mermaid_png(
        output_file_path="repo_analysis_graph.png"
    )

    initial_state = {
        "repo_path": repo_path,
        "files_to_analyze": [],
        "file_analyses": [],
        "final_summary": None,
        "chroma_collection": None,
        "stored_documents": 0,
    }

    print(f"Starting repo analysis for: {repo_path}")
    print("=" * 60)

    # Execute analysis
    result = await graph.ainvoke(initial_state)

    # Print results
    final_summary = result["final_summary"]
    if final_summary:
        print("\n🎯 REPO ANALYSIS COMPLETE!")
        print(f"\n📊 Tech Stack: {', '.join(final_summary.get('tech_stack', [])[:5])}")
        print(f"\n🏗️ Architecture: {final_summary.get('architecture_overview', '')}")
        print(f"\n📈 Top Frameworks:")
        for fw in final_summary.get("top_frameworks", [])[:5]:
            print(f"  • {fw.get('name', fw)}: {fw.get('count', 'N/A')} files")
        print(f"\n💡 Key Concepts:")
        for concept in final_summary.get("key_concepts", [])[:8]:
            print(f"  • {concept.get('concept', concept)}")

        print(
            f"\n💾 Stored in Chroma collection: {result.get('chroma_collection', 'N/A')}"
        )
        print(f"📄 Documents stored: {result.get('stored_documents', 0)}")

    return result


# Main execution function
async def analyze_github_user(username: str, max_repos: int = 10):
    """Run the complete repo analysis for a GitHub user across multiple repos"""

    try:
        # Select repos to analyze
        repo_names = select_repos_to_analyze(username, max_repos)
        print(f"\nAnalyzing {len(repo_names)} repositories for {username}")
        
        graph = create_repo_analysis_graph()

        # Save visualization
        graph.get_graph(xray=True).draw_mermaid_png(
            output_file_path="repo_analysis_graph.png"
        )

        all_results = []
        
        # Analyze each repository
        for i, repo_name in enumerate(repo_names):
            print(f"\n{'='*60}")
            print(f"ANALYZING REPOSITORY {i+1}/{len(repo_names)}: {username}/{repo_name}")
            print(f"{'='*60}")
            
            initial_state = {
                "username": username,
                "repo_name": repo_name,
                "repo_files": [],
                "file_analyses": [],
                "final_summary": None,
                "chroma_collection": None,
                "stored_documents": 0,
            }

            try:
                # Execute analysis for this repo
                result = await graph.ainvoke(initial_state)
                all_results.append(result)
                
                # Print results for this repo
                final_summary = result["final_summary"]
                if final_summary:
                    print(f"\n🎯 ANALYSIS COMPLETE FOR {repo_name}!")
                    print(
                        f"📊 Tech Stack: {', '.join(final_summary.get('tech_stack', [])[:5])}"
                    )
                    print(f"🏗️ Architecture: {final_summary.get('architecture_overview', '')[:100]}...")
                    print(f"📈 Top Frameworks: {', '.join([fw.get('name', str(fw)) for fw in final_summary.get('top_frameworks', [])[:3]])}")
                    print(f"💾 Collection: {result.get('chroma_collection', 'N/A')}")
                    print(f"📄 Documents: {result.get('stored_documents', 0)}")
                else:
                    print(f"⚠️ No summary generated for {repo_name}")
                    
            except Exception as e:
                print(f"❌ Failed to analyze {repo_name}: {e}")
                continue

        # Print overall summary
        print(f"\n{'='*60}")
        print(f"🏁 COMPLETED ANALYSIS OF {len(all_results)}/{len(repo_names)} REPOSITORIES")
        print(f"{'='*60}")
        
        total_documents = sum(r.get('stored_documents', 0) for r in all_results)
        collections = [r.get('chroma_collection') for r in all_results if r.get('chroma_collection')]
        
        print(f"\n📊 OVERALL STATS:")
        print(f"  • Repositories analyzed: {len(all_results)}")
        print(f"  • Total documents stored: {total_documents}")
        print(f"  • Collections created: {len(collections)}")
        
        if collections:
            print(f"\n💾 CHROMA COLLECTIONS:")
            for collection in collections:
                print(f"  • {collection}")

        return {
            "username": username,
            "analyzed_repos": len(all_results),
            "total_repos": len(repo_names),
            "results": all_results,
            "collections": collections,
            "total_documents": total_documents
        }

    except Exception as e:
        print(f"Failed to analyze user {username}: {e}")
        return None


if __name__ == "__main__":
    import asyncio

    # Test with a specific GitHub username
    test_username = "samrae7"

    print(f"Testing GitHub analysis for user: {test_username}")
    asyncio.run(analyze_github_user(test_username))
