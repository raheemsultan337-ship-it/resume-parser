from pydantic import BaseModel, Field, field_validator
from typing import List

class AnalysisResult(BaseModel):
    match_score: int = Field(..., ge=0, le=100)
    missing_keywords: List[str]
    suggestions: List[str]

    @field_validator("missing_keywords", "suggestions")
    @classmethod
    def not_empty_list(cls, v):
        return v if v is not None else []
