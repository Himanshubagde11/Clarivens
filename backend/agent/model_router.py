"""
Clarivens AI Agent — Model Router.

Abstracts all LLM calls behind a single interface.
Models are configured in settings — swap providers without rewriting agent logic.

Implements a multi-model fallback cascade:
  1. Primary model (configured in settings)
  2. Fallback model chain
  3. Deterministic fallback response

Handles 429 rate limits, 503 service unavailable, and model deprecation errors.
"""
import time
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
    Implements a multi-model fallback cascade to handle quota exhaustion gracefully.
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

    # Ordered fallback model chain — tried in sequence if previous fails
    # Verified working models with high availability are placed first.
    MODEL_FALLBACK_CHAIN = [
        "gemini-3.5-flash-lite",   # Ultra-fast (~1.6s), high reliability, active quota
        "gemini-3.5-flash",        # Deep reasoning, verified working
        "gemini-flash-lite-latest",# Latest lite alias, verified working
        "gemini-3.1-flash-lite",   # Lightweight backup, verified working
        "gemini-3.6-flash",        # Balanced (re-try if quota resets)
        "gemini-3.7-flash",        # Fallback
        "gemini-3.8-flash",        # Fallback
    ]

    def __init__(self):
        self._client = None
        # Track which models hit quota or error so we skip them
        self._quota_exhausted: set[str] = set()

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
            return "gemini-3.5-flash" if "gemini-3.5-flash" not in self._quota_exhausted else settings.agent_primary_model, 0.4
        return settings.agent_primary_model, 0.25

    def _get_model_chain(self, primary_model: str) -> list[str]:
        """Returns an ordered list of models to try. Primary model is first."""
        chain = [primary_model] if primary_model not in self._quota_exhausted else []
        for m in self.MODEL_FALLBACK_CHAIN:
            if m not in chain and m not in self._quota_exhausted:
                chain.append(m)
        # If all exhausted, reset cache and try working ones
        if not chain:
            self._quota_exhausted.clear()
            chain = list(self.MODEL_FALLBACK_CHAIN)
        return chain

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

        Implements an ultra-fast multi-model fallback cascade:
          - 429 RESOURCE_EXHAUSTED → marks model as quota-exhausted, tries next immediately
          - 503 HIGH_DEMAND → tries next available model immediately without delay
          - 404 NOT_FOUND (deprecated) → marks and tries next immediately
          - Returns first successful response in ~1.5-2 seconds
        """
        if not self.client:
            return ModelResponse(
                content=self._fallback_response(task),
                model_used="fallback",
                finish_reason="no_api_key",
            )

        primary_model, temperature = self._select_model(task)
        model_chain = self._get_model_chain(primary_model)

        # Build Gemini messages (done once, reused across model attempts)
        gemini_contents = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "assistant":
                role = "model"
            content = msg.get("content", "")
            if content:
                gemini_contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=content)])
                )

        # Build config
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
        )
        if response_schema is not None:
            config.response_mime_type = "application/json"
            config.response_schema = response_schema

        last_error = None

        for model_name in model_chain:
            if model_name in self._quota_exhausted:
                continue

            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=gemini_contents,
                    config=config,
                )

                logger.info("[ModelRouter] Success: model=%s task=%s", model_name, task)
                return ModelResponse(
                    content=response.text,
                    model_used=model_name,
                    tokens_in=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    tokens_out=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                    raw=response,
                )

            except Exception as e:
                err_str = str(e)
                last_error = e

                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    logger.warning(
                        "[ModelRouter] Quota exhausted for model %s (task=%s). Trying next model.",
                        model_name, task
                    )
                    self._quota_exhausted.add(model_name)
                    continue

                elif "404" in err_str or "NOT_FOUND" in err_str or "no longer available" in err_str:
                    logger.warning("[ModelRouter] Model %s not found/deprecated. Trying next model.", model_name)
                    self._quota_exhausted.add(model_name)
                    continue

                elif "503" in err_str or "HIGH_DEMAND" in err_str or "Service Unavailable" in err_str:
                    logger.warning("[ModelRouter] 503 high demand from %s. Trying next model immediately.", model_name)
                    continue

                else:
                    logger.error("[ModelRouter] Unexpected error from %s (task=%s): %s", model_name, task, err_str)
                    continue

        # All models failed
        logger.error("[ModelRouter] All models in chain failed for task '%s'. Last error: %s", task, str(last_error))
        return ModelResponse(
            content=self._fallback_response(task, error_msg=str(last_error)),
            model_used="fallback",
            finish_reason="error",
        )

    def _fallback_response(self, task: str, error_msg: Optional[str] = None) -> str:
        """Returns a safe, helpful deterministic fallback when all models are unavailable."""

        # No API key configured
        if not settings.gemini_api_key:
            return (
                "I'm temporarily unavailable. "
                "Please contact Clarivens directly or try again shortly."
            )

        # Check if it's a quota issue specifically
        if error_msg and ("429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg):
            return (
                "I'm receiving a high volume of requests right now and need a brief moment to recover. "
                "Please try again in a few minutes — I'll be back with you shortly! "
                "Alternatively, feel free to describe your business challenge and I'll help as soon as I'm back."
            )

        # Generic fallback responses by task type — actually helpful
        fallbacks = {
            "greeting": (
                "Hello! I'm Clarivens AI, your dedicated analytics consultant. "
                "I help businesses identify the right data analytics services for their needs. "
                "What business challenge can I help you with today?"
            ),
            "general_faq": (
                "Clarivens is a professional Data Analytics, Business Intelligence, "
                "AI/ML and Data Science company. We help businesses turn raw data into "
                "actionable insights. Our core services include:\n\n"
                "• **Data Cleaning & Preparation** — fix messy datasets\n"
                "• **Exploratory Data Analysis (EDA)** — discover what your data contains\n"
                "• **Sales & Customer Analytics** — understand revenue and churn\n"
                "• **Predictive Analytics** — forecast trends with ML\n"
                "• **BI & Dashboard Development** — live reporting on Power BI / Tableau\n\n"
                "Please describe your business challenge and I'll recommend the right service."
            ),
            "pricing_inquiry": (
                "Our pricing depends on your specific requirements and dataset size. "
                "Please describe your business problem and I'll recommend the appropriate "
                "Clarivens package with accurate pricing."
            ),
            "service_discovery": (
                "I can help you identify the right Clarivens analytics service. "
                "To make the best recommendation, could you tell me:\n\n"
                "1. What is your main business challenge?\n"
                "2. What type of data do you have? (sales, customer, financial, etc.)\n"
                "3. What outcome are you hoping for?"
            ),
            "requirement_analysis": (
                "I'd love to help you find the right solution. "
                "Could you describe your business challenge in a bit more detail? "
                "For example: What data do you have, what question are you trying to answer, "
                "and what decision will this help you make?"
            ),
        }
        return fallbacks.get(
            task,
            "I'm here to help you find the right Clarivens analytics solution. "
            "Please describe your business challenge or data needs and I'll be with you shortly."
        )


# Module-level singleton
model_router = ModelRouter()
