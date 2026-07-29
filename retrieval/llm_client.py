"""
LLM Client — manages interaction with Google Gemini via the OpenAI SDK for query rewriting and text generation.
"""
from openai import OpenAI
from typing import List, Dict, Any

from ingestion.config import GEMINI_API_KEY, GEMINI_BASE_URL, CHAT_MODEL

# Initialize OpenAI client pointing to Gemini endpoint
client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url=GEMINI_BASE_URL,
)

def rewrite_query(user_query: str) -> str:
    """
    Rewrite the user query to expand synonyms, fix typos, and improve retrieval context.
    Returns the expanded query as a single string.
    """
    system_prompt = (
        "You are an expert HR and Startup Operations advisor. "
        "Your task is to rewrite the user's query to optimize it for a vector search and keyword search engine. "
        "Expand abbreviations (e.g., 'esop' -> 'Employee Stock Ownership Plan'), add relevant synonyms, "
        "and formulate a clear, comprehensive search query. "
        "Do NOT answer the query. Just provide the rewritten query."
    )
    
    print(f"[LLM] Rewriting query: '{user_query}'")
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original query: {user_query}"}
        ],
        temperature=0.3,
    )
    rewritten = response.choices[0].message.content.strip()
    print(f"[LLM] Rewritten to: '{rewritten}'")
    return rewritten


def generate_answer(query: str, context_chunks: List[Dict[str, Any]]) -> str:
    """
    Generate the final answer based strictly on the retrieved context chunks.
    """
    system_prompt = (
        "You are an expert Co-founder, HR, and Operations Advisor for a startup. "
        "Answer the user's query based ONLY on the provided context below. "
        "If the answer cannot be found in the context, say 'I cannot find the answer in the handbook.' "
        "Provide a highly structured, practical answer. Use bullet points and frameworks where applicable. "
        "When you use information from a source, add a citation to it at the end of the sentence or paragraph, "
        "like this: [Breadcrumb -> Heading Path]."
    )
    
    context_text = ""
    for idx, chunk in enumerate(context_chunks):
        breadcrumb = chunk.get("breadcrumb", "")
        heading_path = chunk.get("heading_path", "")
        content = chunk.get("content", "")
        context_text += f"\n\n--- Source {idx + 1} ---\nBreadcrumb: {breadcrumb} > {heading_path}\nContent:\n{content}"

    prompt = f"Context:\n{context_text}\n\nUser Query: {query}"
    
    print(f"[LLM] Generating answer using {len(context_chunks)} chunks of context...")
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()
