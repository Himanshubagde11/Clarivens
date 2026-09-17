"""
Clarivens AI Agent — Training & Knowledge Loader

This module loads custom training files (text, markdown) from the 
`backend/training/data` directory and injects them into the AI's 
system prompt. This acts as a Retrieval-Augmented Generation (RAG) 
base, allowing you to 'train' the local model with specific 
company knowledge without requiring expensive weight fine-tuning.
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TRAINING_DIR = Path(__file__).parent / "data"

def get_training_knowledge() -> str:
    """
    Reads all .txt and .md files in the training data directory
    and concatenates them into a single knowledge string.
    """
    knowledge = []
    
    if not TRAINING_DIR.exists():
        TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        return ""
        
    for file_path in TRAINING_DIR.glob("*.*"):
        if file_path.suffix in [".txt", ".md"]:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        knowledge.append(f"--- Document: {file_path.name} ---")
                        knowledge.append(content)
                        knowledge.append("")
            except Exception as e:
                logger.error(f"Failed to load training file {file_path.name}: {e}")
                
    if not knowledge:
        return ""
        
    return "\n".join(knowledge)
