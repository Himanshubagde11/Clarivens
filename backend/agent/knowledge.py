"""
Clarivens AI Agent — Knowledge Retrieval System.

Retrieves relevant Clarivens knowledge from the AgentKnowledge table
using keyword-based search (no external vector DB required for v1).

Architecture:
  User query → keyword extraction → DB search → ranked chunks → agent context

This is designed to be upgraded to embedding-based retrieval (pgvector or similar)
without changing the interface consumed by the orchestrator.
"""
import re
import logging
from typing import Optional
from sqlalchemy.orm import Session

from backend.database import models
from backend.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# Knowledge Retrieval
# ============================================================

def _extract_keywords(query: str) -> list[str]:
    """
    Extracts meaningful keywords from a query for database search.
    Removes stopwords and short tokens.
    """
    STOPWORDS = {
        "i", "me", "my", "myself", "we", "our", "you", "your", "he", "she",
        "it", "they", "what", "which", "who", "how", "when", "where", "why",
        "is", "are", "was", "were", "be", "been", "being", "have", "has",
        "had", "do", "does", "did", "will", "would", "could", "should",
        "may", "might", "shall", "can", "the", "a", "an", "and", "or",
        "but", "in", "on", "at", "to", "for", "of", "with", "by", "from",
        "about", "into", "through", "during", "before", "after", "above",
        "below", "up", "down", "out", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "all", "any", "both",
        "each", "few", "more", "most", "other", "some", "such", "no",
        "not", "only", "same", "so", "than", "too", "very", "just",
        "clarivens", "need", "want", "like", "help", "get", "make",
    }
    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_\-]+\b", query.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def _score_chunk(chunk: models.AgentKnowledge, keywords: list[str]) -> float:
    """
    Scores a knowledge chunk against the keyword list.
    Simple TF-style scoring on title + content + tags.
    """
    score = 0.0
    searchable = (
        (chunk.title or "").lower() + " " +
        (chunk.content or "").lower() + " " +
        " ".join(chunk.tags or []).lower()
    )

    for kw in keywords:
        count = searchable.count(kw)
        if count > 0:
            # Title match is worth more
            title_count = (chunk.title or "").lower().count(kw)
            score += title_count * 2.0 + (count - title_count) * 1.0

    return score


def retrieve_knowledge(
    query: str,
    db: Session,
    category: Optional[str] = None,
    max_chunks: int = 4,
    kb_version: Optional[str] = None,
) -> list[dict]:
    """
    Retrieves the most relevant knowledge chunks for a query.

    Args:
        query: The user's question or conversation context
        db: SQLAlchemy session
        category: Optional category filter (service, methodology, faq, etc.)
        max_chunks: Maximum number of chunks to return
        kb_version: Knowledge base version (defaults to settings)

    Returns:
        List of dicts: [{title, content, category, score}]
    """
    try:
        kb_ver = kb_version or settings.agent_knowledge_version

        query_filter = [
            models.AgentKnowledge.is_active == True,
            models.AgentKnowledge.kb_version == kb_ver,
        ]
        if category:
            query_filter.append(models.AgentKnowledge.category == category)

        chunks = db.query(models.AgentKnowledge).filter(*query_filter).all()

        if not chunks:
            return []

        keywords = _extract_keywords(query)
        if not keywords:
            # No keywords — return top chunks by category relevance
            return [
                {"title": c.title, "content": c.content, "category": c.category, "score": 0.5}
                for c in chunks[:max_chunks]
            ]

        # Score and rank
        scored = [(c, _score_chunk(c, keywords)) for c in chunks]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for chunk, score in scored[:max_chunks]:
            if score > 0:
                results.append({
                    "title": chunk.title,
                    "content": chunk.content[:800],  # Limit context length
                    "category": chunk.category,
                    "score": round(score, 2),
                })

        return results

    except Exception as e:
        logger.error("[Knowledge] Retrieval failed: %s", type(e).__name__)
        return []


def format_knowledge_for_prompt(chunks: list[dict]) -> str:
    """
    Formats retrieved knowledge chunks into a prompt-ready string.
    """
    if not chunks:
        return ""

    lines = ["--- Clarivens Knowledge Base ---"]
    for chunk in chunks:
        lines.append(f"\n[{chunk['category'].upper()}] {chunk['title']}")
        lines.append(chunk["content"])
    lines.append("--- End Knowledge Base ---")
    return "\n".join(lines)
