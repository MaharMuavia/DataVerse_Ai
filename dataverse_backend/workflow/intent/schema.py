from pydantic import BaseModel, field_validator
from typing import Literal, Optional, List

class IntentClassification(BaseModel):
    intent: Literal["EDA", "VIZ", "ML", "XAI", "SQL", "CHITCHAT"]
    sub_intent: str
    target_columns: List[str]
    chart_type: Optional[str]
    model_type: Optional[Literal["classification", "regression"]]
    confidence: float

    @field_validator('target_columns', mode='before')
    @classmethod
    def validate_target_columns(cls, v):
        if isinstance(v, list):
            return [col.strip().lower() for col in v]
        return v