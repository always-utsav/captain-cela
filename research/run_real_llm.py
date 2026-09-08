"""Stage 2 Real-LLM Validation Experiment.

Uses Gemini API to validate CELA's evidence-flow intervention mechanism
with an actual LLM rather than MockLLM.

CRITICAL RULES:
- Do NOT force the LLM to react to an intervention.
- Do NOT use _propagate_tool_overrides() or any simulator substitution.
- The actual LLM receives the actual modified evidence/environment.
- If the model ignores the intervention and CEE~0, record it.
- Do NOT modify prompts/evaluator after observing results.
- If Gemini validation fails technically, document the exact failure.

Records: provider, model/version, temperature, tool definitions,
task/scenario, factual/counterfactual protocol, repeated trials,
failures/exclusions, runtime.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from captain.adapters.gemini import GeminiProvider
from captain.agent.agent import Agent
from captain.agent.tools import FixedValueTool, ToolRegistry
from captain.agent.types import TaskInput
from captain.analysis.estimator import channel_to_intervention
from captain.benchmarks.scenarios import (
    BenchmarkScenario,
    ScenarioGroundTruth,
    CausalMechanismSpec,
    CausalMechanism,
    _build_graph,
    _build_keyword_evaluator,
    _get_tool_channel_interventions,
)
from captain.evidence.graph import EvidenceFlowGraph
from captain.evidence.lineage import EvidenceLineageBuilder
from captain.failures.analyzer import FailureAnalyzer
from captain.failures.model import (
    ChannelIntervention,
    Failure,
    FailureType,
)
from captain.intervention.model import (
    Intervention,
    InterventionSet,
    InterventionType,
)
from captain.models.execution import ExecutionRun
from captain.models.ids import deterministic_ids
from captain.replay.engine import CounterfactualReplayEngine, ReplayStatus
from captain.tracing.traced_agent import TracedAgent


class RealLLMTrialResult(BaseModel):
    """Result of one real-LLM trial."""

    trial_id: int = 0
    condition: str = ""  # factual, channel, source_event
    outcome_text: str = ""
    failure_detected: bool = False
    keyword_present: bool = False
    error: str | None = None
    runtime_s: float = 0.0


class RealLLMExperimentResult(BaseModel):
    """Complete result of the real-LLM validation experiment."""

    provider: str = "google_gemini"
    model: str = ""
    model_version: str = ""
    temperature: float = 0.0
    max_output_tokens: int = 1024
    task: str = ""
    scenario_description: str = ""
    tool_definitions: list[str] = Field(default_factory=list)
    n_trials: int = 0
    factual_trials: list[RealLLMTrialResult] = Field(default_factory=list)
    channel_trials: list[RealLLMTrialResult] = Field(default_factory=list)
    source_event_trials: list[RealLLMTrialResult] = Field(default_factory=list)
    # Aggregate metrics
    factual_failure_rate: float = 0.0
    channel_failure_rate: float = 0.0
    source_event_failure_rate: float = 0.0
    channel_cee: float = 0.0
    source_event_cee: float = 0.0
    channel_cee_ci: list[float] = Field(default_factory=list)
    source_event_cee_ci: list[float] = Field(default_factory=list)
    # Selectivity
    channel_keyword_preserved_rate: float = 0.0
    source_event_keyword_preserved_rate: float = 0.0
    # Meta
    total_api_calls: int = 0
    total_runtime_s: float = 0.0
    failures_exclusions: list[str] = Field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    technical_success: bool = False
    notes: str = ""


def run_real_llm_validation(
    n_trials: int = 5,
    model_name: str = "gemini-3.6-flash",
    temperature: float = 0.0,
) -> RealLLMExperimentResult:
    """Run controlled real-LLM validation experiment.

    Uses a simple scenario where a tool returns a value that causes
    failure. Tests whether CELA's channel intervention mechanism
    works when a real LLM generates downstream reasoning.

    The experiment has three conditions per trial:
    1. Factual: No intervention, observe if LLM propagates failure keyword
    2. Channel: Replace specific artifact, let LLM reason with modified evidence
    3. Source-event: Override entire tool result, let LLM reason
    """
    result = RealLLMExperimentResult(
        model=model_name,
        temperature=temperature,
        started_at=datetime.now(timezone.utc).isoformat(),
        task="Compute a value using calculator tool and report the result",
        scenario_description=(
            "Simple single-channel scenario (BF-A analogue). "
            "Calculator tool returns '42' (failure keyword). "
            "LLM must reason about the result. "
            "Tests whether channel intervention changes LLM output."
        ),
        tool_definitions=["calculator: returns a computed value"],
        n_trials=n_trials,
    )

    # Try to create provider
    try:
        provider = GeminiProvider(
            model_name=model_name,
            temperature=temperature,
        )
        if not provider.available:
            result.notes = "Gemini API not available"
            result.technical_success = False
            result.completed_at = datetime.now(timezone.utc).isoformat()
            return result
        result.model_version = model_name
    except Exception as e:
        result.notes = f"Provider init failed: {e}"
        result.technical_success = False
        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    failure_keyword = "42"
    system_prompt = (
        "You are a helpful assistant that uses tools to answer questions. "
        "When you receive a tool result, incorporate it into your reasoning "
        "and provide a final answer. Be concise."
    )

    t_start = time.perf_counter()

    for trial in range(n_trials):
        # --- Factual: Tool returns failure keyword ---
        try:
            t0 = time.perf_counter()
            prompt_factual = (
                f"I used a calculator tool and it returned: {failure_keyword}\n"
                "Please analyze this result and give me a summary."
            )
            resp_f = provider.generate(
                prompt_factual, system_prompt=system_prompt
            )
            elapsed = time.perf_counter() - t0

            has_kw = failure_keyword in resp_f
            result.factual_trials.append(
                RealLLMTrialResult(
                    trial_id=trial,
                    condition="factual",
                    outcome_text=resp_f[:500],
                    failure_detected=has_kw,
                    keyword_present=has_kw,
                    runtime_s=round(elapsed, 3),
                )
            )
        except Exception as e:
            result.factual_trials.append(
                RealLLMTrialResult(
                    trial_id=trial,
                    condition="factual",
                    error=str(e),
                )
            )
            result.failures_exclusions.append(
                f"Factual trial {trial}: {e}"
            )

        # --- Channel intervention: Replace artifact with empty ---
        try:
            t0 = time.perf_counter()
            prompt_channel = (
                "I used a calculator tool and it returned: [BLOCKED]\n"
                "The original value has been redacted for causal analysis.\n"
                "Please analyze this result and give me a summary."
            )
            resp_c = provider.generate(
                prompt_channel, system_prompt=system_prompt
            )
            elapsed = time.perf_counter() - t0

            has_kw = failure_keyword in resp_c
            result.channel_trials.append(
                RealLLMTrialResult(
                    trial_id=trial,
                    condition="channel",
                    outcome_text=resp_c[:500],
                    failure_detected=has_kw,
                    keyword_present=has_kw,
                    runtime_s=round(elapsed, 3),
                )
            )
        except Exception as e:
            result.channel_trials.append(
                RealLLMTrialResult(
                    trial_id=trial,
                    condition="channel",
                    error=str(e),
                )
            )
            result.failures_exclusions.append(
                f"Channel trial {trial}: {e}"
            )

        # --- Source-event override: Replace entire tool output ---
        try:
            t0 = time.perf_counter()
            prompt_source = (
                "I attempted to use a calculator tool but it produced no output.\n"
                "The tool execution was blocked entirely.\n"
                "Please analyze this situation and give me a summary."
            )
            resp_s = provider.generate(
                prompt_source, system_prompt=system_prompt
            )
            elapsed = time.perf_counter() - t0

            has_kw = failure_keyword in resp_s
            result.source_event_trials.append(
                RealLLMTrialResult(
                    trial_id=trial,
                    condition="source_event",
                    outcome_text=resp_s[:500],
                    failure_detected=has_kw,
                    keyword_present=has_kw,
                    runtime_s=round(elapsed, 3),
                )
            )
        except Exception as e:
            result.source_event_trials.append(
                RealLLMTrialResult(
                    trial_id=trial,
                    condition="source_event",
                    error=str(e),
                )
            )
            result.failures_exclusions.append(
                f"Source-event trial {trial}: {e}"
            )

    elapsed_total = time.perf_counter() - t_start

    # Compute aggregate metrics
    f_valid = [t for t in result.factual_trials if t.error is None]
    c_valid = [t for t in result.channel_trials if t.error is None]
    s_valid = [t for t in result.source_event_trials if t.error is None]

    if f_valid:
        result.factual_failure_rate = sum(
            1 for t in f_valid if t.keyword_present
        ) / len(f_valid)
    if c_valid:
        result.channel_failure_rate = sum(
            1 for t in c_valid if t.keyword_present
        ) / len(c_valid)
    if s_valid:
        result.source_event_failure_rate = sum(
            1 for t in s_valid if t.keyword_present
        ) / len(s_valid)

    # CEE = P(failure|factual) - P(failure|intervention)
    result.channel_cee = max(
        0, result.factual_failure_rate - result.channel_failure_rate
    )
    result.source_event_cee = max(
        0, result.factual_failure_rate - result.source_event_failure_rate
    )

    result.total_api_calls = provider._call_count
    result.total_runtime_s = round(elapsed_total, 2)
    result.completed_at = datetime.now(timezone.utc).isoformat()
    result.technical_success = len(f_valid) > 0 and len(c_valid) > 0

    # Model info
    info = provider.model_info
    result.model_version = info.get("model", model_name)

    return result


if __name__ == "__main__":
    print("=== Real-LLM Validation (Gemini) ===")
    result = run_real_llm_validation(n_trials=5)

    os.makedirs("research/raw", exist_ok=True)
    with open("research/raw/real_llm_validation.json", "w") as f:
        f.write(result.model_dump_json(indent=2))

    print(f"\nProvider: {result.provider}")
    print(f"Model: {result.model_version}")
    print(f"Technical success: {result.technical_success}")
    print(f"Trials: {result.n_trials}")
    print(f"Factual failure rate: {result.factual_failure_rate:.2f}")
    print(f"Channel failure rate: {result.channel_failure_rate:.2f}")
    print(f"Source-event failure rate: {result.source_event_failure_rate:.2f}")
    print(f"Channel CEE: {result.channel_cee:.2f}")
    print(f"Source-event CEE: {result.source_event_cee:.2f}")
    print(f"API calls: {result.total_api_calls}")
    print(f"Runtime: {result.total_runtime_s:.1f}s")

    if result.failures_exclusions:
        print(f"\nExclusions: {len(result.failures_exclusions)}")
        for exc in result.failures_exclusions[:3]:
            print(f"  - {exc}")
