from qdrant_client.models import VectorParams, Distance
from app.ai.qdrant_client import client

client.recreate_collection(
    collection_name="machine_problems",
    vectors_config=VectorParams(
        size=384,
        distance=Distance.COSINE
    )
)

print("Collection Created")