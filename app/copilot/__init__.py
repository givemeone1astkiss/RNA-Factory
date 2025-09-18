"""
Copilot package for AI-powered RNA design assistance.

This package contains the core AI components including:
- LangGraph-based assistant framework
- RAG (Retrieval Augmented Generation) system
- Multimodal RAG capabilities
- Prompt templates and management
"""

from .copilot import RNADesignAssistant
from .rag import RNADesignRAGSystem
from .prompts import (
    RNA_DESIGN_SYSTEM_PROMPT,
    GENERAL_BIOINFO_SYSTEM_PROMPT,
    QUERY_CLASSIFICATION_PROMPT,
    OFF_TOPIC_REDIRECTION,
    RESPONSE_TEMPLATES,
    CAPABILITIES,
    RESPONSE_TYPES,
    TOOL_DESCRIPTIONS,
    LITERATURE_REFERENCE_REQUIRED
)

__all__ = [
    'RNADesignAssistant',
    'RNADesignRAGSystem',
    'RNA_DESIGN_SYSTEM_PROMPT',
    'GENERAL_BIOINFO_SYSTEM_PROMPT',
    'QUERY_CLASSIFICATION_PROMPT',
    'OFF_TOPIC_REDIRECTION',
    'RESPONSE_TEMPLATES',
    'CAPABILITIES',
    'RESPONSE_TYPES',
    'TOOL_DESCRIPTIONS',
    'LITERATURE_REFERENCE_REQUIRED'
]
