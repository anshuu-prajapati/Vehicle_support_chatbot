from app.services.rag_service import ask_question
from app.ai.groq_llm import generate_response


def generate_ai_answer(query):

    rag_result = ask_question(query)

    prompt = f"""
You are an industrial machine support engineer.

Problem:
{rag_result['problem']}

Description:
{rag_result['description']}

Solutions:
{chr(10).join(rag_result['solutions'])}

User Question:
{query}

Provide a professional WhatsApp-friendly response.
"""

    return generate_response(prompt)