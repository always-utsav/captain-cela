"""Generic tool interface and demonstration tools for the CAPTAIN agent.

Provides:

- :class:`Tool` — abstract base class for all tools.
- :class:`ToolRegistry` — a lookup table that maps tool names to instances.
- Three demonstration tools: :class:`CalculatorTool`, :class:`TimestampTool`,
  and :class:`EchoTool`.

The tool interface is intentionally minimal so that future tracing can wrap
every :meth:`Tool.execute` call transparently.
"""

from __future__ import annotations

import abc
import ast
import operator
from datetime import UTC, datetime
from typing import Any

# Separator for multi-output tool results.  When a tool's execute()
# returns a string containing this separator, the TracedAgent splits
# the result into multiple artifacts, each linked to the same source
# event.  This creates genuinely shared-source evidence channels in
# the provenance graph.
MULTI_OUTPUT_SEPARATOR = "|||"


class Tool(abc.ABC):
    """Abstract base class for agent tools.

    Subclasses must define :attr:`name`, :attr:`description`, and implement
    :meth:`execute`.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool."""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Short human-readable description used by the planner."""

    @abc.abstractmethod
    def execute(self, args: dict[str, str]) -> str:
        """Run the tool and return a string result.

        Args:
            args: Named arguments for the tool invocation.

        Returns:
            A string representation of the tool's output.
        """


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Named collection of :class:`Tool` instances.

    Tools are registered by their :attr:`Tool.name` and retrieved via
    :meth:`get`.  Iteration yields all registered tools.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.  Overwrites any existing tool with the same name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Return the tool registered under *name*, or ``None``."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Return all registered tools in registration order."""
        return list(self._tools.values())

    def tool_descriptions(self) -> str:
        """One-line-per-tool summary suitable for inclusion in an LLM prompt."""
        return "\n".join(f"- {t.name}: {t.description}" for t in self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# ---------------------------------------------------------------------------
# Demonstration tools
# ---------------------------------------------------------------------------

# Operators allowed in the safe arithmetic evaluator.
_SAFE_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval_expr(node: ast.AST) -> float:
    """Recursively evaluate an AST node containing only arithmetic."""
    if isinstance(node, ast.Expression):
        return _safe_eval_expr(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp):
        op_fn = _SAFE_OPS.get(type(node.op))
        if op_fn is None:
            msg = f"Unsupported binary operator: {type(node.op).__name__}"
            raise ValueError(msg)
        return float(op_fn(_safe_eval_expr(node.left), _safe_eval_expr(node.right)))
    if isinstance(node, ast.UnaryOp):
        op_fn = _SAFE_OPS.get(type(node.op))
        if op_fn is None:
            msg = f"Unsupported unary operator: {type(node.op).__name__}"
            raise ValueError(msg)
        return float(op_fn(_safe_eval_expr(node.operand)))
    msg = f"Unsupported expression node: {type(node).__name__}"
    raise ValueError(msg)


class CalculatorTool(Tool):
    """Evaluates basic arithmetic expressions safely.

    Supports ``+``, ``-``, ``*``, ``/``, ``%``, ``**`` on numeric literals.
    Does **not** use ``eval()``; instead parses the expression into an AST
    and walks only the numeric/operator nodes.

    Expected arg: ``{"expression": "2 + 3 * 4"}``
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate a basic arithmetic expression (e.g. '2 + 3 * 4')."

    def execute(self, args: dict[str, str]) -> str:
        expr = args.get("expression", "")
        if not expr:
            return "Error: no expression provided"
        try:
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval_expr(tree)
            # Return integer representation when the result is whole.
            if result == int(result):
                return str(int(result))
            return str(result)
        except (ValueError, SyntaxError, ZeroDivisionError) as exc:
            return f"Error: {exc}"


class TimestampTool(Tool):
    """Returns the current UTC timestamp.

    If *frozen_time* is provided at construction, that fixed value is
    returned instead — useful for deterministic testing.

    Expected arg: ``{}`` (no arguments required).
    """

    def __init__(self, frozen_time: datetime | None = None) -> None:
        self._frozen_time = frozen_time

    @property
    def name(self) -> str:
        return "timestamp"

    @property
    def description(self) -> str:
        return "Return the current UTC timestamp."

    def execute(self, args: dict[str, str]) -> str:
        ts = self._frozen_time if self._frozen_time else datetime.now(UTC)
        return ts.isoformat()


class EchoTool(Tool):
    """Echoes the input back unchanged.

    Expected arg: ``{"message": "hello"}``
    """

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echo the input message back."

    def execute(self, args: dict[str, str]) -> str:
        return args.get("message", "")


class FixedValueTool(Tool):
    """Tool that always returns a pre-configured value.

    Used in benchmark scenarios to ensure tool results match the
    values referenced in the MockLLM's scripted responses.  This
    makes the agent execution genuinely dependent on tool outputs:
    if the tool result is overridden during counterfactual replay,
    the downstream text changes accordingly.

    This is NOT a test-only convenience — it establishes the causal
    dependency chain:

        tool result → LLM reasoning → evaluator outcome

    Without it, the tool result and LLM response are disconnected.
    """

    def __init__(self, tool_name: str, value: str, desc: str = "") -> None:
        self._name = tool_name
        self._value = value
        self._desc = desc or f"Returns: {value}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._desc

    def execute(self, args: dict[str, str]) -> str:
        return self._value


def create_default_tool_registry(
    *,
    frozen_time: datetime | None = None,
) -> ToolRegistry:
    """Build a :class:`ToolRegistry` pre-loaded with the demo tools.

    Args:
        frozen_time: If given, the :class:`TimestampTool` returns this
            fixed value instead of the real clock.

    Returns:
        A registry containing ``calculator``, ``timestamp``, and ``echo``.
    """
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(TimestampTool(frozen_time=frozen_time))
    registry.register(EchoTool())
    return registry
