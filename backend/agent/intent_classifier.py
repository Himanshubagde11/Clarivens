"""
Clarivens AI Agent — Intent Classifier.

Classifies user messages into structured intents using a two-stage approach:
1. Fast deterministic keyword matching (no LLM cost)
2. LLM-assisted classification for ambiguous messages

Intent taxonomy drives the orchestrator's routing decisions.
"""
import re
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================
# Intent Definitions
# ============================================================

class Intent:
    SERVICE_DISCOVERY    = "service_discovery"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    PACKAGE_INQUIRY      = "package_inquiry"
    PRICING_INQUIRY      = "pricing_inquiry"
    DATA_UPLOAD          = "data_upload"
    DATA_QUESTION        = "data_question"
    PROJECT_STATUS       = "project_status"
    RESULT_EXPLANATION   = "result_explanation"
    LEAD_CAPTURE         = "lead_capture"
    GENERAL_FAQ          = "general_faq"
    FEEDBACK             = "feedback"
    GREETING             = "greeting"
    CONTACT_REQUEST      = "contact_request"
    FORECASTING          = "forecasting"
    ML_PREDICTION        = "ml_prediction"
    DASHBOARD_REQUEST    = "dashboard_request"
    REPORT_REQUEST       = "report_request"
    UNKNOWN              = "unknown"


@dataclass
class ClassificationResult:
    intent: str
    confidence: float           # 0.0–1.0
    sub_intents: list[str] = field(default_factory=list)
    extracted_entities: dict    = field(default_factory=dict)
    method: str = "deterministic"  # deterministic | llm | hybrid


# ============================================================
# Keyword Patterns (deterministic, no LLM cost)
# ============================================================

INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    (Intent.GREETING, [
        r"\b(hello|hi|hey|good morning|good afternoon|howdy)\b",
        r"^(hi|hey|hello)\s*[!.]?$",
    ]),
    (Intent.PRICING_INQUIRY, [
        r"\b(price|pricing|cost|how much|quote|budget|fee|charge|invoice)\b",
        r"\b(what does .+ cost|how much .+ (cost|charge))\b",
    ]),
    (Intent.PACKAGE_INQUIRY, [
        r"\b(package|plan|tier|subscription|basic|premium|enterprise|starter)\b",
        r"\b(what.*(package|plan)|which package|packages available)\b",
    ]),
    (Intent.DATA_UPLOAD, [
        r"\b(upload|attach|send|share|provide).*(file|data|csv|excel|dataset|spreadsheet)\b",
        r"\b(i have|i.ve got|my).*(file|data|csv|excel|xlsx|dataset|spreadsheet)\b",
        r"\b(here.?s my|here is my|here are my).*(data|file|csv|excel)\b",
    ]),
    (Intent.DATA_QUESTION, [
        r"\b(which|what|show me|tell me|find|calculate|compute|compare|analyse|analyze)\b.*(region|product|customer|revenue|sales|profit|trend|top|bottom|best|worst|highest|lowest|average|total|count|sum)\b",
        r"\b(what (is|are) (my|the) (top|best|worst|highest|lowest|average|total))\b",
        r"\b(how (many|much|often|frequently)).*(in my data|in the data|in this dataset)\b",
    ]),
    (Intent.PROJECT_STATUS, [
        r"\b(status|progress|done|finished|complete|ready|how long|when)\b.*(project|analysis|report|dashboard)\b",
        r"\b(is my|is the).*(project|analysis|report|ready|done|complete)\b",
    ]),
    (Intent.RESULT_EXPLANATION, [
        r"\b(explain|what does|what do|what is|interpret|meaning of|understand|walk me through)\b.*(result|finding|insight|prediction|forecast|metric|kpi|chart|graph|number|r2|rmse|accuracy)\b",
        r"\b(what does this (mean|show|indicate))\b",
    ]),
    (Intent.FORECASTING, [
        r"\b(forecast|predict|projection|next (month|quarter|year|week)|future|will be|going to be|expected)\b.*(sales|revenue|demand|growth|trend)\b",
        r"\b(sales|revenue|demand).*(forecast|prediction|next|future|next year)\b",
    ]),
    (Intent.ML_PREDICTION, [
        r"\b(churn|predict|machine learning|ml|model|classification|regression|anomaly|outlier)\b",
        r"\b(predict (which|who|what|when|how many))\b",
        r"\b(customers? (likely|who will|are going to) (leave|churn|buy|convert))\b",
    ]),
    (Intent.DASHBOARD_REQUEST, [
        r"\b(dashboard|visualization|chart|graph|kpi|monitor|track|live|real.?time)\b",
        r"\b(build|create|make|set up).*(dashboard|report|visualization)\b",
    ]),
    (Intent.REPORT_REQUEST, [
        r"\b(report|summary|generate report|export|pdf|presentation|deck)\b",
        r"\b(generate|create|send|download).*(report|summary|pdf)\b",
    ]),
    (Intent.LEAD_CAPTURE, [
        r"\b(contact me|reach out|get in touch|my email|my phone|sign up|register|book a call|schedule)\b",
        r"\b(name is|email is|i.?m from|my company)\b",
    ]),
    (Intent.CONTACT_REQUEST, [
        r"\b(speak to|talk to|connect with|book a (call|meeting|demo)|schedule a call)\b.*(team|someone|expert|consultant|person|you)\b",
    ]),
    (Intent.FEEDBACK, [
        r"\b(not helpful|wrong|incorrect|that.?s wrong|this is wrong|bad answer|improve|feedback)\b",
        r"\b(thumbs (up|down)|great answer|perfect|very helpful|thank you)\b",
    ]),
    (Intent.GENERAL_FAQ, [
        r"\b(what (is|are) clarivens|about clarivens|who (are|is) clarivens|do you (offer|provide|do)|what (can|do) you)\b",
        r"\b(how does.*(clarivens|it|this) work|what services|clarivens do)\b",
    ]),
    (Intent.REQUIREMENT_ANALYSIS, [
        r"\b(i need|i want|i.?m looking for|i.?m trying to|my (business|company|team) needs|help (me|us) (with|understand))\b",
        r"\b(problem|challenge|issue|struggling|difficulty).*(data|sales|revenue|customer|business)\b",
        r"\b(revenue (is|has been) (falling|declining|dropping|down)|losing customers|customers (are|have been) (leaving|churning))\b",
    ]),
]


# ============================================================
# Service / Industry Entity Extraction
# ============================================================

INDUSTRY_PATTERNS: dict[str, list[str]] = {
    "ecommerce":       [r"\b(ecommerce|e-commerce|online store|shopify|amazon|marketplace|retail online)\b"],
    "retail":          [r"\b(retail|store|shop|brick.and.mortar|physical store|pos)\b"],
    "saas":            [r"\b(saas|software|subscription|mrr|arr|churn|user (growth|retention))\b"],
    "finance":         [r"\b(finance|financial|banking|investment|accounting|revenue|profit|margin|cost)\b"],
    "healthcare":      [r"\b(healthcare|health|hospital|clinic|patient|medical|pharma)\b"],
    "manufacturing":   [r"\b(manufacturing|factory|production|supply chain|inventory|warehouse|logistics)\b"],
    "hr":              [r"\b(hr|human resources|employee|workforce|attrition|hiring|recruitment|payroll)\b"],
    "marketing":       [r"\b(marketing|campaign|ads|advertisement|ctr|conversion|funnel|leads|email marketing)\b"],
}

DATASET_TYPE_PATTERNS: dict[str, list[str]] = {
    "sales":      [r"\b(sales|revenue|transaction|order|purchase|invoice)\b"],
    "customer":   [r"\b(customer|client|user|subscriber|churn|retention)\b"],
    "financial":  [r"\b(financial|profit|loss|p&l|balance sheet|cash flow)\b"],
    "marketing":  [r"\b(campaign|ad|click|impression|conversion|lead)\b"],
    "hr":         [r"\b(employee|staff|headcount|turnover|attrition|salary)\b"],
    "inventory":  [r"\b(inventory|stock|warehouse|supply chain|logistics|shipment)\b"],
    "web":        [r"\b(website|web|page views|sessions|bounce rate|analytics)\b"],
}


def _extract_entities(text: str) -> dict:
    """Extract industry and dataset type hints from message text."""
    text_l = text.lower()
    entities: dict = {}

    for industry, patterns in INDUSTRY_PATTERNS.items():
        for p in patterns:
            if re.search(p, text_l):
                entities["industry"] = industry
                break
        if "industry" in entities:
            break

    for ds_type, patterns in DATASET_TYPE_PATTERNS.items():
        for p in patterns:
            if re.search(p, text_l):
                entities.setdefault("dataset_type", []).append(ds_type)

    return entities


def classify_intent_deterministic(text: str) -> ClassificationResult:
    """
    Fast deterministic classification using regex patterns.
    Returns the highest-confidence match.
    """
    text_lower = text.lower().strip()
    matched_intents: list[tuple[str, float]] = []

    for intent, patterns in INTENT_PATTERNS:
        score = 0.0
        for pattern in patterns:
            if re.search(pattern, text_lower):
                score += 1.0
        if score > 0:
            matched_intents.append((intent, min(score / len(patterns) + 0.5, 1.0)))

    entities = _extract_entities(text)

    if not matched_intents:
        return ClassificationResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            extracted_entities=entities,
            method="deterministic",
        )

    # Sort by confidence descending
    matched_intents.sort(key=lambda x: x[1], reverse=True)
    top_intent, top_confidence = matched_intents[0]
    sub_intents = [i for i, _ in matched_intents[1:3]]

    # Boost confidence for multi-pattern matches
    return ClassificationResult(
        intent=top_intent,
        confidence=min(top_confidence, 0.95),
        sub_intents=sub_intents,
        extracted_entities=entities,
        method="deterministic",
    )


def classify_intent(text: str, use_llm_fallback: bool = False) -> ClassificationResult:
    """
    Public classifier entry point.
    Uses deterministic matching first. LLM fallback is reserved for
    future implementation when confidence is very low.
    """
    result = classify_intent_deterministic(text)

    # If confidence is below threshold and LLM fallback is requested,
    # we can add LLM classification here in a future version.
    # For now, return deterministic result or REQUIREMENT_ANALYSIS as fallback.
    if result.intent == Intent.UNKNOWN and len(text.split()) > 5:
        # Longer text with no match is likely a requirement description
        entities = _extract_entities(text)
        return ClassificationResult(
            intent=Intent.REQUIREMENT_ANALYSIS,
            confidence=0.4,
            extracted_entities=entities,
            method="heuristic_fallback",
        )

    return result
