import operator
import os
import ast
from typing import Annotated, List, Dict, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from collections import Counter

from langchain_openai import ChatOpenAI
from langgraph.types import Send
from langgraph.graph import StateGraph, START, END

MODEL = "o4-mini"
llm = ChatOpenAI(model=MODEL)

# Pydantic models for structured output
class FileAnalysis(BaseModel):
    frameworks: List[str] = Field(description="List of frameworks/libraries detected")
    concepts: List[str] = Field(description="Key concepts, patterns, or functionality")
    architecture_patterns: List[str] = Field(description="Design patterns or architectural concepts")
    file_purpose: str = Field(description="What this file does in 1-2 sentences")

class ConceptSummary(BaseModel):
    top_frameworks: List[Dict[str, int]] = Field(description="Most used frameworks with counts")
    key_concepts: List[Dict[str, int]] = Field(description="Important concepts with frequency")
    architecture_overview: str = Field(description="Overall project architecture summary")
    tech_stack: List[str] = Field(description="Main technologies used")

# Overall repo analysis state
class RepoAnalysisState(TypedDict):
    repo_path: str
    files_to_analyze: List[str]
    file_analyses: Annotated[List[Dict], operator.add]  # Collected results from map step
    final_summary: Optional[ConceptSummary]
    embeddings: List[Dict]

# Individual file analysis state (sent to each analyze_file_node)
class FileState(TypedDict):
    file_path: str
    file_content: str
    file_type: str

# NODE FUNCTIONS

def discover_files(state: RepoAnalysisState) -> RepoAnalysisState:
    """Find all relevant code files in the repo"""
    repo_path = state["repo_path"]
    
    # File extensions we care about
    relevant_extensions = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', 
        '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.dart', '.vue',
        '.json', '.yaml', '.yml', '.toml', '.md'
    }
    
    # Directories to ignore
    ignore_dirs = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
        'build', 'dist', '.next', 'target', 'vendor', '.pytest_cache'
    }
    
    files_to_analyze = []
    
    for root, dirs, files in os.walk(repo_path):
        # Remove ignored directories from traversal
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if any(file.endswith(ext) for ext in relevant_extensions):
                file_path = os.path.join(root, file)
                files_to_analyze.append(file_path)
    
    print(f"Found {len(files_to_analyze)} files to analyze")
    return {**state, "files_to_analyze": files_to_analyze}

def static_analysis(file_path: str, content: str) -> Dict:
    """Quick static analysis to extract imports and basic info"""
    file_ext = os.path.splitext(file_path)[1]
    frameworks = []
    
    if file_ext == '.py':
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        frameworks.append(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        frameworks.append(node.module.split('.')[0])
        except:
            pass
    
    elif file_ext in ['.js', '.ts', '.tsx', '.jsx']:
        # Simple regex-based import extraction
        import re
        import_patterns = [
            r"import.*from ['\"]([^'\"]+)['\"]",
            r"require\(['\"]([^'\"]+)['\"]\)",
            r"import ['\"]([^'\"]+)['\"]"
        ]
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            frameworks.extend([m.split('/')[0] for m in matches if not m.startswith('.')])
    
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
        response = await llm.with_structured_output(FileAnalysis).ainvoke(analysis_prompt)
        
        return {
            "file_analyses": [{
                "file_path": file_path,
                "file_type": file_type,
                "analysis": response.dict(),
                "static_frameworks": static_info.get('static_frameworks', [])
            }]
        }
    except Exception as e:
        print(f"Analysis failed for {file_path}: {e}")
        return {
            "file_analyses": [{
                "file_path": file_path,
                "file_type": file_type,
                "analysis": {
                    "frameworks": static_info.get('static_frameworks', []),
                    "concepts": [],
                    "architecture_patterns": [],
                    "file_purpose": f"Failed to analyze: {str(e)}"
                },
                "static_frameworks": static_info.get('static_frameworks', [])
            }]
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
        summary = await llm.with_structured_output(ConceptSummary).ainvoke(summary_prompt)
        
        return {
            **state, 
            "final_summary": summary.dict()
        }
    except Exception as e:
        # Fallback summary
        return {
            **state,
            "final_summary": {
                "top_frameworks": [{"name": k, "count": v} for k, v in framework_counts.most_common(10)],
                "key_concepts": [{"concept": k, "count": v} for k, v in concept_counts.most_common(15)],
                "architecture_overview": f"Analysis of {len(file_analyses)} files completed with some errors",
                "tech_stack": list(framework_counts.keys())[:10]
            }
        }

async def generate_embeddings(state: RepoAnalysisState) -> RepoAnalysisState:
    """Generate embeddings for RAG system (Phase 3)"""
    # This would integrate with your embedding service
    # For now, just prepare the data structure
    
    final_summary = state["final_summary"]
    file_analyses = state["file_analyses"]
    
    # Prepare embedding content
    embedding_docs = []
    
    # Add summary-level embeddings
    if final_summary:
        embedding_docs.append({
            "type": "project_summary",
            "content": f"Tech stack: {', '.join(final_summary.get('tech_stack', []))}. Architecture: {final_summary.get('architecture_overview', '')}",
            "metadata": {"level": "project", "type": "overview"}
        })
        
        # Add concept embeddings
        for concept in final_summary.get('key_concepts', []):
            embedding_docs.append({
                "type": "concept",
                "content": f"Project uses concept: {concept.get('concept', concept)}",
                "metadata": {"level": "concept", "frequency": concept.get('count', 1)}
            })
    
    # Add file-level embeddings
    for analysis in file_analyses:
        if "analysis" in analysis:
            file_purpose = analysis["analysis"].get("file_purpose", "")
            frameworks = analysis["analysis"].get("frameworks", [])
            
            embedding_docs.append({
                "type": "file_analysis", 
                "content": f"File {os.path.basename(analysis['file_path'])}: {file_purpose}. Uses: {', '.join(frameworks)}",
                "metadata": {"file_path": analysis["file_path"], "level": "file"}
            })
    
    return {**state, "embeddings": embedding_docs}

# Mapping function for Send API
def continue_to_file_analysis(state: RepoAnalysisState):
    """Map discovered files to parallel analysis tasks"""
    files_to_analyze = state["files_to_analyze"]
    
    # Read file contents and create Send objects
    send_objects = []
    for file_path in files_to_analyze:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            file_ext = os.path.splitext(file_path)[1]
            
            send_objects.append(Send("analyze_file", {
                "file_path": file_path,
                "file_content": content,
                "file_type": file_ext
            }))
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")
    
    return send_objects

# Build the repo analysis graph
def create_repo_analysis_graph():
    """Create the repo analysis graph with map-reduce pattern"""
    
    graph = StateGraph(RepoAnalysisState)
    
    # Add nodes
    graph.add_node("discover_files", discover_files)
    graph.add_node("analyze_file", analyze_file_node)  # Gets called multiple times via Send
    graph.add_node("summarize_analysis", summarize_analysis)
    graph.add_node("generate_embeddings", generate_embeddings)
    
    # Add edges
    graph.add_edge(START, "discover_files")
    
    # Map step: Send each file to parallel analysis
    graph.add_conditional_edges(
        "discover_files",
        continue_to_file_analysis,
        ["analyze_file"]
    )
    
    # Reduce step: All analyze_file nodes flow to summary
    graph.add_edge("analyze_file", "summarize_analysis")
    graph.add_edge("summarize_analysis", "generate_embeddings")
    graph.add_edge("generate_embeddings", END)
    
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
        "embeddings": []
    }
    
    print(f"Starting repo analysis for: {repo_path}")
    print("="*60)
    
    # Execute analysis
    result = await graph.ainvoke(initial_state)
    
    # Print results
    final_summary = result["final_summary"]
    if final_summary:
        print("\n🎯 REPO ANALYSIS COMPLETE!")
        print(f"\n📊 Tech Stack: {', '.join(final_summary.get('tech_stack', [])[:5])}")
        print(f"\n🏗️ Architecture: {final_summary.get('architecture_overview', '')}")
        print(f"\n📈 Top Frameworks:")
        for fw in final_summary.get('top_frameworks', [])[:5]:
            print(f"  • {fw.get('name', fw)}: {fw.get('count', 'N/A')} files")
        print(f"\n💡 Key Concepts:")
        for concept in final_summary.get('key_concepts', [])[:8]:
            print(f"  • {concept.get('concept', concept)}")
        
        print(f"\n🔍 Generated {len(result['embeddings'])} embeddings for RAG system")
    
    return result

# Example usage
if __name__ == "__main__":
    import asyncio
    
    # Test with current directory or specify a repo path
    repo_path = "/Users/william/repos/mock_project"  # Change this!
    # repo_path = "."  # Current directory
    
    asyncio.run(analyze_repo(repo_path))