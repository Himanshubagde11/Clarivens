"""
Clarivens AI Agent — Conversation State Machine.

Defines all valid conversation states and the allowed transitions.
The orchestrator uses this to know what stage the conversation is in
and what actions are appropriate.
"""
from enum import Enum


class ConversationState(str, Enum):
    """All possible states in a Clarivens AI conversation."""
    DISCOVERY = "discovery"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    SERVICE_MATCH = "service_match"
    PACKAGE_MATCH = "package_match"
    DATA_REQUEST = "data_request"
    DATA_ANALYSIS = "data_analysis"
    RESULT_EXPLANATION = "result_explanation"
    REPORT = "report"
    FOLLOW_UP = "follow_up"
    LEAD_CAPTURE = "lead_capture"


# Valid state transitions: state → set of allowed next states
STATE_TRANSITIONS: dict[ConversationState, set[ConversationState]] = {
    ConversationState.DISCOVERY: {
        ConversationState.REQUIREMENT_ANALYSIS,
        ConversationState.LEAD_CAPTURE,
        ConversationState.DISCOVERY,
    },
    ConversationState.REQUIREMENT_ANALYSIS: {
        ConversationState.SERVICE_MATCH,
        ConversationState.DATA_REQUEST,
        ConversationState.LEAD_CAPTURE,
        ConversationState.REQUIREMENT_ANALYSIS,
        ConversationState.DISCOVERY,
    },
    ConversationState.SERVICE_MATCH: {
        ConversationState.PACKAGE_MATCH,
        ConversationState.DATA_REQUEST,
        ConversationState.LEAD_CAPTURE,
        ConversationState.SERVICE_MATCH,
        ConversationState.REQUIREMENT_ANALYSIS,
    },
    ConversationState.PACKAGE_MATCH: {
        ConversationState.LEAD_CAPTURE,
        ConversationState.DATA_REQUEST,
        ConversationState.PACKAGE_MATCH,
        ConversationState.SERVICE_MATCH,
    },
    ConversationState.DATA_REQUEST: {
        ConversationState.DATA_ANALYSIS,
        ConversationState.LEAD_CAPTURE,
        ConversationState.DATA_REQUEST,
    },
    ConversationState.DATA_ANALYSIS: {
        ConversationState.RESULT_EXPLANATION,
        ConversationState.DATA_ANALYSIS,
    },
    ConversationState.RESULT_EXPLANATION: {
        ConversationState.REPORT,
        ConversationState.FOLLOW_UP,
        ConversationState.RESULT_EXPLANATION,
    },
    ConversationState.REPORT: {
        ConversationState.FOLLOW_UP,
        ConversationState.REPORT,
    },
    ConversationState.FOLLOW_UP: {
        ConversationState.FOLLOW_UP,
        ConversationState.SERVICE_MATCH,
        ConversationState.DISCOVERY,
    },
    ConversationState.LEAD_CAPTURE: {
        ConversationState.SERVICE_MATCH,
        ConversationState.DATA_REQUEST,
        ConversationState.FOLLOW_UP,
    },
}


def can_transition(from_state: ConversationState, to_state: ConversationState) -> bool:
    """Returns True if the transition from_state → to_state is allowed."""
    return to_state in STATE_TRANSITIONS.get(from_state, set())


def advance_state(
    current_state: ConversationState,
    intent: str,
    has_project: bool = False,
    has_dataset: bool = False,
    has_lead_info: bool = False,
) -> ConversationState:
    """
    Determines the next appropriate state based on current state + intent.
    Returns the same state if no valid transition applies.
    """
    intent_l = intent.lower()

    # Lead capture signals
    if intent_l in ("lead_capture", "contact_request"):
        if can_transition(current_state, ConversationState.LEAD_CAPTURE):
            return ConversationState.LEAD_CAPTURE

    # Data-related intents
    if intent_l in ("data_question", "data_upload") and has_dataset:
        if can_transition(current_state, ConversationState.DATA_ANALYSIS):
            return ConversationState.DATA_ANALYSIS
        if can_transition(current_state, ConversationState.DATA_REQUEST):
            return ConversationState.DATA_REQUEST

    if intent_l == "data_upload" and not has_dataset:
        if can_transition(current_state, ConversationState.DATA_REQUEST):
            return ConversationState.DATA_REQUEST

    # Result/report intents
    if intent_l in ("result_explanation", "project_status") and has_project:
        if can_transition(current_state, ConversationState.RESULT_EXPLANATION):
            return ConversationState.RESULT_EXPLANATION

    # Package / pricing intent
    if intent_l == "package_inquiry":
        if can_transition(current_state, ConversationState.PACKAGE_MATCH):
            return ConversationState.PACKAGE_MATCH

    # Service discovery intent
    if intent_l == "requirement_analysis":
        if can_transition(current_state, ConversationState.REQUIREMENT_ANALYSIS):
            return ConversationState.REQUIREMENT_ANALYSIS

    if intent_l == "service_discovery":
        if can_transition(current_state, ConversationState.SERVICE_MATCH):
            return ConversationState.SERVICE_MATCH

    # Default: stay in current state
    return current_state
