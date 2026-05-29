from app.ai.embeddings import create_embedding
from app.ai.qdrant_client import client


def search_problem(query: str):

    query_vector = create_embedding(query)

    results = client.query_points(
        collection_name="machine_problems",
        query=query_vector,
        limit=3
    )

    return results