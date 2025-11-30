"""
Sub-agents package for notarial assistant.
"""

from .calendar_agent import calendar_agent
from .gmail_agent import gmail_agent

__all__ = [
    "calendar_agent",
    "gmail_agent",
]
