"""Pydantic schemas for the News Intelligence Agent."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class NewsArticle(BaseModel):
    """Single news article analysis."""
    title: str = Field(..., description="Article headline")
    impact: str = Field(..., description="Market impact: positive, negative, or neutral")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    
    @field_validator('impact')
    @classmethod
    def validate_impact(cls, v: str) -> str:
        valid_impacts = ['positive', 'negative', 'neutral']
        if v not in valid_impacts:
            raise ValueError(f'impact must be one of {valid_impacts}')
        return v


class NewsAgentInput(BaseModel):
    """Input for the News Agent."""
    company: str = Field(..., description="Company name or ticker symbol")
    query: Optional[str] = Field(None, description="Optional natural language query")


class NewsAgentOutput(BaseModel):
    """Output from the News Agent."""
    company: str = Field(..., description="Company analyzed")
    articles: List[NewsArticle] = Field(default_factory=list, description="Analyzed articles")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class WorkerResponse(BaseModel):
    """Standardized worker response compatible with Manager Agent."""
    status: str = Field(..., description="Status: 'success' or 'error'")
    data: Optional[Dict[str, Any]] = Field(None, description="Result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage and cost")
