"""
Demo: Gemini 2.5 Flash API with Google Search Grounding
Reads GEMINI_API_KEY from .env
"""
import os
import requests
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def ask_gemini_with_search(prompt: str):
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }
    # Ask user if they want to enable thinking
    enable_thinking = input("Enable Gemini 'thinking' (y/n)? ").strip().lower() == 'y'
    thinking_budget = 1024
    if enable_thinking:
        try:
            val = input("Thinking budget (tokens, default 1024, -1 for dynamic): ").strip()
            if val:
                thinking_budget = int(val)
        except Exception:
            pass
    data = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "tools": [
            {"google_search": {}}
        ]
    }
    if enable_thinking:
        data["generationConfig"] = {
            "thinkingConfig": {
                "thinkingBudget": thinking_budget,
                "includeThoughts": True
            }
        }
    response = requests.post(API_URL, headers=headers, json=data, timeout=60)
    response.raise_for_status()
    return response.json()


def print_grounded_response(resp):
    candidate = resp["candidates"][0]
    parts = candidate["content"]["parts"]
    # Print answer and thought summaries if present
    print("\nGemini Answer:")
    for part in parts:
        if part.get("thought"):
            print("\n[Gemini Thought Summary]:")
            print(part["text"])
        elif part.get("text"):
            print(part["text"])
    if "groundingMetadata" in candidate:
        print("\nSources:")
        chunks = candidate["groundingMetadata"].get("groundingChunks", [])
        for i, chunk in enumerate(chunks):
            web = chunk.get("web")
            if web:
                print(f"[{i+1}] {web.get('title')}: {web.get('uri')}")
    else:
        print("No sources/citations returned.")


if __name__ == "__main__":
    user_prompt = input("Ask Gemini (grounded with Google Search): ")
    try:
        resp = ask_gemini_with_search(user_prompt)
        print_grounded_response(resp)
    except Exception as e:
        print(f"Error: {e}")
