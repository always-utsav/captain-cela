"""CAPTAIN execution tracing infrastructure.

This sub-package provides the observation layer (Layer B) that records
canonical traces of agent executions without altering agent behavior.

Core types::

    from captain.tracing import TraceCollector, TracedAgent
"""

from captain.tracing.collector import TraceCollector
from captain.tracing.traced_agent import TracedAgent

__all__ = [
    "TraceCollector",
    "TracedAgent",
]
