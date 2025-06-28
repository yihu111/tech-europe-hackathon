import os
from typing import List, Dict, Optional
from pydantic import BaseModel

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

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

                    collection_scores.append(
                        {
                            "collection_name": collection_name,
                            "repo_name": repo_name,
                            "best_score": float(best_score),
                            "best_match_type": doc_type,
                            "best_match_content": doc.page_content[:100] + "...",
                        }
                    )

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
    interview_question: str,
    collection_name: str,
    k: int = 10,
    score_threshold: float = 0.5,
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

        # Use the original query directly for better semantic matching
        # Over-enhancement can dilute the query's semantic meaning
        search_query = interview_question

        # Perform similarity search
        results = vector_store.similarity_search_with_score(search_query, k=k)

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


def search_across_all_relevant_collections(
    interview_question: str, k_per_collection: int = 5, score_threshold: float = 0.5
) -> List[SearchResult]:
    """
    Search across all available collections for relevant contributions.

    Args:
        interview_question: The interview question to find relevant experience for
        k_per_collection: Number of results per collection
        score_threshold: Maximum similarity score to include (lower = more similar)

    Returns:
        Flattened list of SearchResult objects ordered by relevance
    """
    collections = list_relevant_collections(interview_question)
    all_results = []

    for collection_info in collections:
        collection_name = collection_info["collection_name"]
        try:
            search_response = search_user_contributions(
                interview_question, collection_name, k_per_collection, score_threshold
            )
            if search_response.total_results > 0:
                all_results.extend(search_response.results)
        except Exception as e:
            print(f"Error searching collection {collection_name}: {e}")
            continue

    # Sort all results by score (lower is better)
    all_results.sort(key=lambda x: x.score)

    return all_results


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

    # Demo queries
    demo_queries = [
        "Tell me about React development experience",
        "What machine learning or AI projects have been worked on?",
        "Show me examples of API development and backend services",
        "What experience is there with databases and data storage?",
    ]

    all_results = search_across_all_relevant_collections(
        demo_queries[0], k_per_collection=2, score_threshold=1.0
    )

    for result in all_results:
        print(f"  - {result.type}: {result.content}")


if __name__ == "__main__":
    main()
