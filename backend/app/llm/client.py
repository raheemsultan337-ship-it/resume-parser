import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Set it in the environment or in a .env file before calling the LLM client."
        )

    _client = genai.Client(api_key=api_key)
    return _client


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Returns raw text response from Gemini."""
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config={
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
        },
    )
    return response.text