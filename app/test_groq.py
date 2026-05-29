from app.ai.groq_llm import generate_response

answer = generate_response(
    "How can you help me?"
)

print(answer)