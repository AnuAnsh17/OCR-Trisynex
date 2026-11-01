from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    name: str
    status: str  # passed, warning, failed, conflict
    field: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None


class ValidationResult(BaseModel):
    status: str = "passed"  # passed, passed_with_warnings, failed, conflict
    checks: List[ValidationCheck] = Field(default_factory=list)
