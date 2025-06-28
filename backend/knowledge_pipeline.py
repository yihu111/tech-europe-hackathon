import operator
import os
import ast
import hashlib
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
    chroma_collection: Optional[str]  # Collection name in Chroma
    stored_documents: int

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
                "analysis": response.model_dump(),
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

async def store_in_chroma(state: RepoAnalysisState) -> RepoAnalysisState:
    """Store all analysis results in Chroma using LangChain integration"""
    
    repo_path = state["repo_path"]
    final_summary = state["final_summary"]
    file_analyses = state["file_analyses"]
    
    # Create collection name from repo path
    repo_name = os.path.basename(repo_path.rstrip('/'))
    collection_name = f"repo_{repo_name}_{hashlib.md5(repo_path.encode()).hexdigest()[:8]}"
    
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
            Project: {repo_name}
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
                    "repo_path": repo_path,
                    "level": "project"
                }
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
                File: {os.path.relpath(file_path, repo_path)}
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
                        "file_type": analysis.get('file_type', ''),
                        "repo_name": repo_name,
                        "repo_path": repo_path,
                        "level": "file",
                        # Convert lists to strings for Chroma compatibility
                        "frameworks": ', '.join(file_analysis.get('frameworks', [])),
                        "concepts": ', '.join(file_analysis.get('concepts', []))
                    }
                )
                
                documents.append(file_doc)
                document_ids.append(f"{collection_name}_file_{i}")
        
        # 3. Store concept-level documents for better retrieval
        if final_summary:
            for j, concept in enumerate(final_summary.get('key_concepts', [])):
                concept_name = concept.get('concept', str(concept))
                concept_count = concept.get('count', 1)
                
                concept_doc_text = f"""
                Concept: {concept_name}
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
                        "repo_path": repo_path,
                        "level": "concept"
                    }
                )
                
                documents.append(concept_doc)
                document_ids.append(f"{collection_name}_concept_{j}")
        
        # Store in Chroma using LangChain's add_documents
        if documents:
            vector_store.add_documents(
                documents=documents,
                ids=document_ids
            )
            
            print(f"✅ Stored {len(documents)} documents in Chroma")
            print(f"   - Project summary: 1")
            print(f"   - File analyses: {len(file_analyses)}")
            print(f"   - Concept documents: {len(documents) - len(file_analyses) - 1}")
            print(f"   - Collection: {collection_name}")
            print(f"   - Persist directory: {CHROMA_DB_PATH}")
        
        return {
            **state, 
            "chroma_collection": collection_name,
            "stored_documents": len(documents)
        }
        
    except Exception as e:
        print(f"❌ Failed to store in Chroma: {e}")
        return {**state, "chroma_collection": None, "stored_documents": 0}

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
    graph.add_node("store_in_chroma", store_in_chroma)
    
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
    graph.add_edge("summarize_analysis", "store_in_chroma")
    graph.add_edge("store_in_chroma", END)
    
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
        "stored_documents": 0
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
        
        print(f"\n💾 Stored in Chroma collection: {result.get('chroma_collection', 'N/A')}")
        print(f"📄 Documents stored: {result.get('stored_documents', 0)}")
    
    return result

# Example usage
if __name__ == "__main__":
    import asyncio
    
    # Test with current directory or specify a repo path
    repo_path = os.getenv("TEST_REPO_PATH")  # Change this!
    # repo_path = "."  # Current directory
    
    asyncio.run(analyze_repo(repo_path))