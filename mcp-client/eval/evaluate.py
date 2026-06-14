"""DeepEval evaluation harness for the multi-agent LangGraph pipeline.

Usage
-----
    # From the mcp-client directory:
    python -m eval.evaluate

    # Skip pipeline re-run and re-score an existing results.json:
    python -m eval.evaluate --reuse-outputs

Prerequisites
-------------
- MCP server running at MCP_SERVER_URL (default: http://localhost:9000)
- Azure OpenAI credentials in environment or .env
- No Redis / PostgreSQL required (MemorySaver + mocked persistence)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

# ── Import path setup ─────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT.parent / ".env", override=False)
    load_dotenv(_ROOT / ".env", override=False)
except ImportError:
    pass

try:
    from deepeval import evaluate
    from deepeval.evaluate.configs import AsyncConfig
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
    from deepeval.models import AzureOpenAIModel
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
except ImportError:
    print(
        "deepeval is not installed. Run:\n"
        "  uv add deepeval  (inside mcp-client/)\n"
        "  or: pip install deepeval",
        file=sys.stderr,
    )
    raise SystemExit(1)

EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.json"
RESULTS_PATH = EVAL_DIR / "results.json"

# Auto-approve HITL interrupts up to this many rounds per test case.
_MAX_HITL_ROUNDS = 5


# ── Model factory (mirrors generate_dataset.py) ───────────────────────────────

def _build_eval_model() -> AzureOpenAIModel:
    api_key = os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
    deployment = os.getenv("AZURE_CHAT_LIGHT_MODEL", "gpt-4o")

    if not api_key:
        raise EnvironmentError("AZURE_API_KEY (or AZURE_OPENAI_API_KEY) is not set.")
    if not endpoint:
        raise EnvironmentError("AZURE_ENDPOINT (or AZURE_OPENAI_ENDPOINT) is not set.")

    return AzureOpenAIModel(
        model=deployment,
        deployment_name=deployment,
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )


# ── Pipeline bootstrap ────────────────────────────────────────────────────────

async def _bootstrap_pipeline() -> None:
    """Initialise agents and workflow with MemorySaver (no Redis needed)."""
    from langgraph.checkpoint.memory import MemorySaver
    from src.declarative.mcp_tools import prepare_workflow

    await prepare_workflow(MemorySaver())


# ── Single test case runner ───────────────────────────────────────────────────

async def _run_case(graph, input_text: str) -> tuple[str, list[str]]:
    """Invoke the pipeline for one input, auto-approving any HITL interrupts.

    Returns:
        (actual_output, retrieval_context)
        where retrieval_context is the per-agent responses used by the aggregator.
    """
    from langchain_core.messages import HumanMessage
    from langgraph.types import Command

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    current_input: dict | Command = {
        "query": input_text,
        "thread_id": thread_id,
        "messages": [HumanMessage(content=input_text)],
    }

    for round_no in range(_MAX_HITL_ROUNDS + 1):
        result = await graph.ainvoke(current_input, config)
        snap = await graph.aget_state(config)

        if not snap.next:
            final: str = result.get("final_response", "")
            agent_responses: dict = result.get("agent_responses", {})
            retrieval_ctx = [f"[{k}]: {v}" for k, v in agent_responses.items() if v]
            return final, retrieval_ctx

        if round_no == _MAX_HITL_ROUNDS:
            break

        # Auto-approve all pending HITL interrupts (covers parallel multi-agent case).
        decisions_by_agent: dict[str, list] = {}
        flat_decisions: list[dict] = []
        for task in snap.tasks:
            for intr in task.interrupts:
                val = intr.value
                agent = val.get("agent", "")
                n = len(val.get("action_requests", []))
                approvals = [{"type": "approve"}] * n
                decisions_by_agent.setdefault(agent, []).extend(approvals)
                flat_decisions.extend(approvals)

        current_input = Command(
            resume={"decisions_by_agent": decisions_by_agent, "decisions": flat_decisions}
        )

    return "", []


# ── Batch runner ──────────────────────────────────────────────────────────────

async def _collect_outputs(goldens: list[dict]) -> list[dict]:
    """Run every golden through the pipeline and attach actual_output + retrieval_context."""
    from src.declarative.workflow import graph

    results: list[dict] = []

    for i, g in enumerate(goldens):
        print(f"  [{i + 1}/{len(goldens)}] {g['input'][:80]}...")
        try:
            with (
                patch("src.core.chat_persistence.save_conversation", new=AsyncMock(return_value=None)),
                patch("src.core.chat_persistence.ensure_thread", new=AsyncMock(return_value=None)),
            ):
                actual, retrieval_ctx = await _run_case(graph, g["input"])
        except Exception as exc:
            print(f"    ERROR: {exc}")
            actual, retrieval_ctx = "", []

        if actual:
            print(f"    -> {actual[:100]}...")
        else:
            print("    -> (no output — case marked as failed)")

        results.append({**g, "actual_output": actual, "retrieval_context": retrieval_ctx})

    return results


# ── Test case builder ─────────────────────────────────────────────────────────

def _build_test_cases(results: list[dict]) -> list[LLMTestCase]:
    cases: list[LLMTestCase] = []
    skipped = 0
    for r in results:
        if not r.get("actual_output"):
            skipped += 1
            continue

        raw_ctx = r.get("context") or []
        context = raw_ctx if isinstance(raw_ctx, list) else [raw_ctx]
        retrieval_ctx = r.get("retrieval_context") or []

        cases.append(
            LLMTestCase(
                input=r["input"],
                actual_output=r["actual_output"],
                expected_output=r.get("expected_output") or "",
                context=context,
                retrieval_context=retrieval_ctx,
            )
        )

    if skipped:
        print(f"  Skipped {skipped} cases with empty actual_output.")
    return cases


# ── Metrics ───────────────────────────────────────────────────────────────────

def _build_metrics(model: AzureOpenAIModel) -> list:
    answer_relevancy = AnswerRelevancyMetric(
        threshold=0.7,
        model=model,
        include_reason=True,
    )

    faithfulness = FaithfulnessMetric(
        threshold=0.7,
        model=model,
        include_reason=True,
    )

    routing_correctness = GEval(
        name="RoutingCorrectness",
        criteria=(
            "Given the user query and the actual output from a multi-agent system, "
            "evaluate whether the response directly addresses the primary domain of "
            "the query (sales analytics, inventory management, customer support, or "
            "marketing/policy knowledge). "
            "Score HIGH when the answer is on-domain and provides concrete data or "
            "actionable information. Score LOW when the answer is generic, off-topic, "
            "or defers to 'contact your team' without providing substantive information."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.6,
        model=model,
    )

    policy_adherence = GEval(
        name="PolicyAdherence",
        criteria=(
            "Evaluate whether the actual output correctly applies or references "
            "relevant business policies when the query involves policy-sensitive "
            "operations (discounts above 25%, refunds, HITL-required approvals, "
            "loyalty tier changes, campaign budget modifications). "
            "Score HIGH when applicable policies are cited and respected. "
            "Score HIGH also when the query has no policy implication (not applicable). "
            "Score LOW only when a clear policy constraint exists but was ignored or "
            "violated in the response."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.6,
        model=model,
    )

    completeness = GEval(
        name="Completeness",
        criteria=(
            "Compare the actual output to the expected output. "
            "Evaluate whether the actual output covers the key facts, entities, and "
            "conclusions present in the expected output. Minor wording differences are "
            "fine. Penalise only significant omissions of relevant information."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=0.6,
        model=model,
    )

    return [answer_relevancy, faithfulness, routing_correctness, policy_adherence, completeness]


# ── Entry point ───────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DeepEval pipeline evaluator")
    p.add_argument(
        "--reuse-outputs",
        action="store_true",
        help="Load results.json instead of re-running the pipeline (re-score only).",
    )
    p.add_argument(
        "--dataset",
        default=str(DATASET_PATH),
        help=f"Path to dataset JSON file (default: {DATASET_PATH})",
    )
    p.add_argument(
        "--results",
        default=str(RESULTS_PATH),
        help=f"Path to write/read results JSON (default: {RESULTS_PATH})",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    dataset_path = Path(args.dataset)
    results_path = Path(args.results)

    # 1. Load goldens
    print(f"Loading dataset from {dataset_path} ...")
    goldens: list[dict] = json.loads(dataset_path.read_text(encoding="utf-8"))
    print(f"  {len(goldens)} goldens loaded.")

    # 2. Collect actual outputs (or reuse existing)
    if args.reuse_outputs and results_path.exists():
        print(f"Reusing existing outputs from {results_path} ...")
        results: list[dict] = json.loads(results_path.read_text(encoding="utf-8"))
    else:
        print("Bootstrapping pipeline (MCP server must be running) ...")
        asyncio.run(_bootstrap_pipeline())
        print(f"Running {len(goldens)} test cases through the pipeline ...")
        results = asyncio.run(_collect_outputs(goldens))
        results_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        print(f"Raw outputs saved to {results_path}")

    # 3. Build LLMTestCase objects
    print("Building test cases ...")
    test_cases = _build_test_cases(results)
    print(f"  {len(test_cases)} test cases ready for evaluation.")

    if not test_cases:
        print("No test cases to evaluate — all pipeline runs failed. Exiting.")
        raise SystemExit(1)

    # 4. Define metrics
    print("Configuring evaluation metrics ...")
    eval_model = _build_eval_model()
    metrics = _build_metrics(eval_model)
    metric_names = [m.name if hasattr(m, "name") else type(m).__name__ for m in metrics]
    print(f"  Metrics: {', '.join(metric_names)}")

    # 5. Run DeepEval
    print("\nRunning DeepEval evaluation ...\n")
    async_config = AsyncConfig(
        max_concurrent=1,
        throttle_value=1.0,  # Increased throttle to give more time between requests
    )
    try:
        evaluate(test_cases=test_cases, metrics=metrics, async_config=async_config)
    except TimeoutError as e:
        print(f"\n❌ Evaluation timed out: {e}")
        print(f"   Partial results may be in {results_path}")
        print("   Try reducing metrics or running with fewer test cases.")
        raise SystemExit(1)
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        print(f"   Partial results may be in {results_path}")
        raise


if __name__ == "__main__":
    main()