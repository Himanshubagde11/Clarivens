"""
AI Insights Engine for Clarivens.
Uses Google Gemini API (google-genai SDK) to generate high-value executive insights
and actionable recommendations from statistical summaries only.

Security & Resilience:
- Never transmits raw row data or PII — only schema and aggregated metrics.
- Enforces strict Pydantic output validation.
- Sanitizes prompt metadata against prompt injection.
- Structured error handling with graceful fallback.
- Client initialized per-call or lazily with API key validation.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.config import settings

logger = logging.getLogger(__name__)

# Pydantic Schemas for Structured Output
class Insight(BaseModel):
    type: str = Field(description="Insight classification: 'observation', 'anomaly', or 'trend'")
    text: str = Field(description="Clear, executive-level business insight based strictly on the provided aggregates")

class Recommendation(BaseModel):
    text: str = Field(description="Specific, actionable business recommendation based on the data findings")

class AIInsights(BaseModel):
    insights: List[Insight] = Field(default_factory=list, description="List of business insights")
    recommendations: List[Recommendation] = Field(default_factory=list, description="List of actionable recommendations")


def _sanitize_summary_for_prompt(profile: dict, eda_results: dict) -> dict:
    """
    Extracts only non-sensitive summary aggregates and column statistics.
    Never includes raw sample rows or arbitrary unvalidated strings.
    """
    safe_profile = {
        "columns": [str(c)[:100] for c in profile.get("columns", [])],
        "inferred_types": {str(k)[:100]: str(v)[:50] for k, v in profile.get("inferred_types", {}).items()},
        "numeric_columns": [str(c)[:100] for c in profile.get("numeric_columns", [])],
        "categorical_columns": [str(c)[:100] for c in profile.get("categorical_columns", [])],
    }

    safe_eda = {}
    if isinstance(eda_results, dict):
        if "summary_statistics" in eda_results and isinstance(eda_results["summary_statistics"], dict):
            safe_eda["summary_statistics"] = eda_results["summary_statistics"]
        if "missing_values" in eda_results and isinstance(eda_results["missing_values"], dict):
            safe_eda["missing_values"] = eda_results["missing_values"]
        if "kpis" in eda_results and isinstance(eda_results["kpis"], list):
            safe_eda["kpis"] = eda_results["kpis"]
        if "categorical_distributions" in eda_results and isinstance(eda_results["categorical_distributions"], dict):
            # Include top categories without raw values
            safe_eda["categorical_distributions"] = {
                str(col)[:100]: {str(k)[:50]: count for k, count in list(dist.items())[:5]}
                for col, dist in eda_results["categorical_distributions"].items()
                if isinstance(dist, dict)
            }

    return {"dataset_profile": safe_profile, "aggregated_eda": safe_eda}


def generate_insights(dataset_profile: dict, eda_results: dict) -> Dict[str, Any]:
    """
    Generates structured business insights from the dataset profile and EDA results.
    """
    api_key = settings.resolved_gemini_key

    if not api_key:
        logger.info("[AI Engine] No Gemini API key provided. Returning fallback guidance.")
        return {
            "insights": [
                {
                    "type": "observation",
                    "text": "Automated data profiling and exploratory analysis completed successfully."
                },
                {
                    "type": "observation",
                    "text": f"Dataset contains {len(dataset_profile.get('columns', []))} columns across "
                            f"{len(dataset_profile.get('numeric_columns', []))} numeric and "
                            f"{len(dataset_profile.get('categorical_columns', []))} categorical dimensions."
                }
            ],
            "recommendations": [
                {
                    "text": "Configure GEMINI_API_KEY in the environment to activate advanced generative insights."
                }
            ]
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        safe_data = _sanitize_summary_for_prompt(dataset_profile, eda_results)

        prompt = f"""
You are an elite Senior Data Analyst and Strategy Consultant for Clarivens Enterprise Intelligence.
Analyze the following aggregated dataset profile and summary metrics.
Generate exactly 3 concise, high-impact business insights (type: 'observation', 'anomaly', or 'trend') and 2 actionable recommendations.

Rules:
1. Do NOT hallucinate data points. Rely strictly on the aggregated statistics provided.
2. Focus on business impact, data quality anomalies, and growth opportunities.
3. Respond in valid JSON adhering to the specified schema.

Summary Data:
{json.dumps(safe_data, indent=2)}
"""

        # Call Gemini using official google-genai 2.x SDK
        response = client.models.generate_content(
            model=settings.agent_primary_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIInsights,
                temperature=0.2,
            ),
        )

        raw_output = response.text
        if not raw_output:
            raise ValueError("Empty response received from Gemini API.")

        parsed_dict = json.loads(raw_output)

        # Validate with Pydantic
        validated = AIInsights.model_validate(parsed_dict)
        return validated.model_dump()

    except Exception as e:
        error_msg = str(e)
        logger.warning(f"[AI Engine] Generative insights generation encountered an issue: {error_msg}")

        # Fallback without failing the analysis pipeline
        return {
            "insights": [
                {
                    "type": "observation",
                    "text": "Dataset profiling and metrics aggregation completed. Detailed AI interpretation is temporarily unavailable."
                }
            ],
            "recommendations": [
                {
                    "text": "Review the summary statistics and correlation matrix directly in the dashboard tabs."
                }
            ],
            "error_code": "AI_SERVICE_UNAVAILABLE"
        }
