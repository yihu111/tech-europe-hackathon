import os
from typing import List, Dict, Optional
from pydantic import BaseModel

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# Match the setup from knowledge_pipeline.py
CHROMA_DB_PATH = "./chroma_langchain_db"
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


class SearchResult(BaseModel):
    content: str
    score: float
    metadata: Dict
    type: str  # project_summary, file_analysis, concept


class VectorSearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    collection_name: str
    total_results: int


def list_available_collections() -> List[str]:
    """List all available ChromaDB collections"""
    try:
        if not os.path.exists(CHROMA_DB_PATH):
            return []

        # Create a dummy Chroma instance to access collections
        temp_store = Chroma(
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH,
        )

        # Get all collection names starting with 'repo_'
        collections = []
        chroma_client = temp_store._client
        all_collections = chroma_client.list_collections()

        for collection in all_collections:
            if collection.name.startswith("repo_"):
                collections.append(collection.name)

        return collections
    except Exception as e:
        print(f"Error listing collections: {e}")
        return []


def list_relevant_collections(query: str, max_collections: int = 10) -> List[Dict]:
    """
    List collections ranked by relevance to the query
    
    Args:
        query: The search query to rank collections against
        max_collections: Maximum number of collections to return
    
    Returns:
        List of dicts with collection info sorted by relevance
    """
    try:
        all_collections = list_available_collections()
        if not all_collections:
            return []
        
        collection_scores = []
        
        for collection_name in all_collections:
            try:
                # Get the best matching document from this collection
                vector_store = Chroma(
                    collection_name=collection_name,
                    embedding_function=embeddings,
                    persist_directory=CHROMA_DB_PATH,
                )
                
                # Search for the single most relevant document in this collection
                results = vector_store.similarity_search_with_score(query, k=1)
                
                if results:
                    doc, best_score = results[0]
                    repo_name = doc.metadata.get("repo_name", "Unknown")
                    doc_type = doc.metadata.get("type", "unknown")
                    
                    collection_scores.append({
                        "collection_name": collection_name,
                        "repo_name": repo_name,
                        "best_score": float(best_score),
                        "best_match_type": doc_type,
                        "best_match_content": doc.page_content[:100] + "..."
                    })
                
            except Exception as e:
                print(f"Error evaluating collection {collection_name}: {e}")
                continue
        
        # Sort by best score (lower is better for similarity)
        collection_scores.sort(key=lambda x: x["best_score"])
        
        return collection_scores[:max_collections]
        
    except Exception as e:
        print(f"Error ranking collections: {e}")
        return []


def search_user_contributions(
    interview_question: str, collection_name: str, k: int = 10, score_threshold: float = 0.5
) -> VectorSearchResponse:
    """
    Search for relevant user contributions based on an interview question.

    Args:
        interview_question: The interview question to find relevant experience for
        collection_name: ChromaDB collection name to search
        k: Number of results to return
        score_threshold: Maximum similarity score to include (lower = more similar)

    Returns:
        VectorSearchResponse with ranked results
    """
    try:
        # Create vector store instance
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH,
        )

        # Enhance the query for better retrieval
        enhanced_query = f"""
        Interview question: {interview_question}
        
        Looking for relevant programming experience, projects, frameworks, and technical concepts 
        that would demonstrate skills and knowledge related to this question.
        """

        # Perform similarity search
        results = vector_store.similarity_search_with_score(enhanced_query, k=k)

        search_results = []
        for doc, score in results:
            # Filter by score threshold (lower scores = better similarity)
            if score <= score_threshold:
                search_results.append(
                    SearchResult(
                        content=doc.page_content,
                        score=float(score),
                        metadata=doc.metadata,
                        type=doc.metadata.get("type", "unknown"),
                    )
                )

        return VectorSearchResponse(
            query=interview_question,
            results=search_results,
            collection_name=collection_name,
            total_results=len(search_results),
        )

    except Exception as e:
        print(f"Error searching collection {collection_name}: {e}")
        return VectorSearchResponse(
            query=interview_question,
            results=[],
            collection_name=collection_name,
            total_results=0,
        )


def search_across_all_collections(
    interview_question: str, k_per_collection: int = 5, score_threshold: float = 0.5
) -> Dict[str, VectorSearchResponse]:
    """
    Search across all available collections for relevant contributions.

    Args:
        interview_question: The interview question to find relevant experience for
        k_per_collection: Number of results per collection
        score_threshold: Maximum similarity score to include (lower = more similar)

    Returns:
        Dictionary mapping collection names to search responses
    """
    collections = list_available_collections()
    results = {}

    for collection_name in collections:
        try:
            search_response = search_user_contributions(
                interview_question, collection_name, k_per_collection, score_threshold
            )
            if search_response.total_results > 0:
                results[collection_name] = search_response
        except Exception as e:
            print(f"Error searching collection {collection_name}: {e}")
            continue

    return results


def get_collection_info(collection_name: str) -> Optional[Dict]:
    """Get metadata about a specific collection"""
    try:
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH,
        )

        # Get some sample documents to understand the collection
        sample_docs = vector_store.similarity_search("", k=3)

        repo_name = None
        doc_types = set()
        total_docs = len(sample_docs)  # This is just a sample, not actual count

        for doc in sample_docs:
            if doc.metadata.get("repo_name"):
                repo_name = doc.metadata["repo_name"]
            if doc.metadata.get("type"):
                doc_types.add(doc.metadata["type"])

        return {
            "collection_name": collection_name,
            "repo_name": repo_name,
            "document_types": list(doc_types),
            "sample_document_count": total_docs,
        }

    except Exception as e:
        print(f"Error getting info for collection {collection_name}: {e}")
        return None


def main():
    """Demo function to test vector search with dummy queries"""
    print("Vector Search Demo")
    print("=" * 50)

    # List available collections
    print("\n1. Available Collections:")
    collections = list_available_collections()
    if not collections:
        print("No collections found. Run knowledge_pipeline.py first to create some.")
        return

    for i, collection in enumerate(collections, 1):
        print(f"   {i}. {collection}")
        info = get_collection_info(collection)
        if info:
            print(f"      - Repo: {info.get('repo_name', 'Unknown')}")
            print(f"      - Types: {', '.join(info.get('document_types', []))}")

    # Demo queries
    demo_queries = [
        "Tell me about React development experience",
        "What machine learning or AI projects have been worked on?",
        "Show me examples of API development and backend services",
        "What experience is there with databases and data storage?",
    ]

    print(f"\n2. Demo Queries:")
    for i, query in enumerate(demo_queries, 1):
        print(f"   {i}. {query}")

    # Demo relevant collections ranking
    sample_query = demo_queries[0]
    print(f"\n3. Collections Ranked by Relevance to: '{sample_query}'")
    print("-" * 70)
    
    relevant_collections = list_relevant_collections(sample_query, max_collections=5)
    
    if relevant_collections:
        for i, collection_info in enumerate(relevant_collections, 1):
            print(f"\n{i}. {collection_info['repo_name']} (Score: {collection_info['best_score']:.4f})")
            print(f"   Collection: {collection_info['collection_name']}")
            print(f"   Best Match Type: {collection_info['best_match_type']}")
            print(f"   Best Match: {collection_info['best_match_content']}")
    else:
        print("No relevant collections found.")

    # Run a sample search on the most relevant collection
    print(f"\n4. Detailed Search in Most Relevant Collection:")
    print("-" * 70)

    if relevant_collections:
        top_collection = relevant_collections[0]["collection_name"]
        results = search_user_contributions(sample_query, top_collection, k=3, score_threshold=0.4)

        print(f"Collection: {results.collection_name}")
        print(f"Total Results: {results.total_results}")

        for i, result in enumerate(results.results, 1):
            print(f"\nResult {i} (Score: {result.score:.4f}):")
            print(f"Type: {result.type}")
            print(f"Content: {result.content[:200]}...")

    # Demo cross-collection search
    print(f"\n5. Cross-Collection Search Results:")
    print("-" * 70)

    all_results = search_across_all_collections(sample_query, k_per_collection=2, score_threshold=0.4)

    for collection_name, response in all_results.items():
        print(f"\nCollection: {collection_name}")
        print(f"Results: {response.total_results}")
        for result in response.results:
            print(f"  - {result.type}: {result.content[:100]}...")


if __name__ == "__main__":
    main()
