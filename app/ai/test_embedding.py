# app/ai/test_embedding.py

from app.ai.embeddings import create_embedding

vector = create_embedding(
    "Machine Overheating"
)

print(len(vector))