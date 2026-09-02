"""
LLM Brain package — Gemini-driven agentic orchestrator for the AI Employee.

Replaces hardcoded cloud_orchestrator.py / local_orchestrator.py routing with
a Gemini 2.5 Flash function-calling loop that calls existing MCP servers as tools.
"""

from llm_brain.brain import LLMBrain

__all__ = ["LLMBrain"]
