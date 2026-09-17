"""
Clarivens AI Agent — Model Router.

Abstracts all LLM calls behind a single interface.
Models are configured in settings — swap providers without rewriting agent logic.

Now using Google Gemini API for fast, reliable production inference.
"""
import logging
import json
from typing import Any, Optional
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    content: str
    model_used: str
    tokens_in: int = 0
    tokens_out: int = 0
    finish_reason: str = "stop"
    raw: Any = None


class ModelRouter:
    """
    Routes LLM calls to the appropriate Gemini model based on task complexity.
    """

    FAST_TASKS = {
        "greeting", "general_faq", "pricing_inquiry", "package_inquiry",
        "project_status", "feedback",
    }

    PRIMARY_TASKS = {
        "service_discovery", "requirement_analysis", "service_match",
        "package_match", "result_explanation", "report_request",
        "dashboard_request", "lead_capture", "contact_request",
        "data_question", "unknown",
    }

    REASONING_TASKS = {
        "forecasting", "ml_prediction", "data_analysis",
        "requirement_analysis_complex",
    }
    
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not settings.gemini_api_key:
                logger.warning("Gemini API key is not set. Using fallback responses.")
                return None
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def _select_model(self, task: str) -> tuple[str, float]:
        """Returns (model_name, temperature) for the given task."""
        if task in self.FAST_TASKS:
            return settings.agent_fast_model, 0.3
        if task in self.REASONING_TASKS:
            return settings.agent_primary_model, 0.4
        return settings.agent_primary_model, 0.25

    def call(
        self,
        messages: list[dict],
        task: str = "service_discovery",
        system_prompt: Optional[str] = None,
        response_schema: Any = None,
        max_tokens: int = 1024,
    ) -> ModelResponse:
        """
        Makes a model call with the appropriate model for the task.

        Args:
            messages: List of {"role": "user"|"assistant", "content": str}
            task: Intent/task name for model routing
            system_prompt: System prompt to prepend (Clarivens consultant identity)
            response_schema: Pydantic schema for structured JSON output
            max_tokens: Maximum output tokens

        Returns:
            ModelResponse with content and usage metadata
        """
        if not self.client:
             return ModelResponse(
                content=self._fallback_response(task),
                model_used="fallback",
                finish_reason="no_api_key",
            )

        try:
            model_name, temperature = self._select_model(task)

            # Build messages for Gemini format
            gemini_contents = []
            
            for msg in messages:
                # Map roles correctly. Usually user and model.
                role = msg.get("role", "user")
                if role == "assistant":
                    role = "model"
                gemini_contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
                )

            # Build configuration
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_prompt,
            )
            
            # If JSON structured output is requested
            if response_schema is not None:
                config.response_mime_type = "application/json"
                config.response_schema = response_schema

            # Make HTTP call to Gemini API
            response = self.client.models.generate_content(
                model=model_name,
                contents=gemini_contents,
                config=config,
            )
            
            return ModelResponse(
                content=response.text,
                model_used=model_name,
                tokens_in=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                tokens_out=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                raw=response,
            )

        except Exception as e:
            logger.error("[ModelRouter] Gemini Model call failed for task '%s': %s", task, str(e))
            return ModelResponse(
                content=self._fallback_response(task),
                model_used="fallback",
                finish_reason="error",
            )

    def _fallback_response(self, task: str) -> str:
        """Returns a safe deterministic fallback when the model is unavailable."""
        fallbacks = {
            "greeting": (
                "Hello! I'm Clarivens AI, your analytics consultant. "
                "How can I help you today?"
            ),
            "general_faq": (
                "Clarivens is a professional Data Analytics, Business Intelligence, "
                "AI/ML and Data Science company. We help businesses turn raw data into "
                "actionable insights. Please describe your business challenge and I'll "
                "identify the right Clarivens service for you."
            ),
            "pricing_inquiry": (
                "Our pricing depends on your specific requirements. Please describe your "
                "business problem and dataset, and I'll recommend the appropriate package "
                "with accurate pricing from our service catalog."
            ),
        }
        return fallbacks.get(
            task,
            "I'm here to help you find the right Clarivens analytics solution. "
            "Please describe your business challenge or data needs."
        )


# Module-level singleton
model_router = ModelRouter()
