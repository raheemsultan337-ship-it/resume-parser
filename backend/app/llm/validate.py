import json
import re
from pydantic import ValidationError
from app.llm.schema import AnalysisResult
from app.llm.client import call_llm
from app.llm.prompt import SYSTEM_PROMPT, build_user_prompt

MAX_RETRIES = 3

def extract_json(raw_text: str) -> str:
    """Strip markdown fences / stray text if the model adds them anyway."""
    text = raw_text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def analyze_resume(resume_text: str, job_description: str) -> AnalysisResult:
    user_prompt = build_user_prompt(resume_text, job_description)
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        raw = call_llm(SYSTEM_PROMPT, user_prompt)
        cleaned = extract_json(raw)

        try:
            data = json.loads(cleaned)
            return AnalysisResult(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            user_prompt = (
                build_user_prompt(resume_text, job_description)
                + f"\n\nYour previous response was invalid ({e}). "
                  "Return ONLY the raw JSON object, nothing else."
            )
            continue

    raise RuntimeError(f"LLM failed to return valid JSON after {MAX_RETRIES} attempts: {last_error}")
