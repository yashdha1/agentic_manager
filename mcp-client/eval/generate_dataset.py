import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    _root = Path(__file__).parent.parent.parent
    load_dotenv(_root / ".env", override=False)
except ImportError:
    pass

CONTEXTS_DIR = Path(__file__).parent / "contexts"
OUTPUT_PATH = Path(__file__).parent / "dataset.json"
MAX_GOLDENS_PER_DOC = 5

try:
    from deepeval.dataset import EvaluationDataset
    from deepeval.models import AzureOpenAIEmbeddingModel, AzureOpenAIModel
    from deepeval.synthesizer import Synthesizer
    from deepeval.synthesizer.config import ContextConstructionConfig
except ImportError as exc:
    print(
        "deepeval is not installed. Run:\n"
        "  uv add deepeval  (inside mcp-client/)\n"
        "  or: pip install deepeval",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


def _build_model() -> AzureOpenAIModel:
    api_key = os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
    deployment = os.getenv("AZURE_CHAT_LIGHT_MODEL", "gpt-4o")

    if not api_key:
        raise EnvironmentError(
            "AZURE_API_KEY (or AZURE_OPENAI_API_KEY) is not set. Check your .env file."
        )
    if not endpoint:
        raise EnvironmentError(
            "AZURE_ENDPOINT (or AZURE_OPENAI_ENDPOINT) is not set. Check your .env file."
        )
    return AzureOpenAIModel(
        model=deployment,
        deployment_name=deployment,
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )


def _build_embedder() -> AzureOpenAIEmbeddingModel:
    api_key = os.getenv("AZURE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
    embedding_model = os.getenv("AZURE_EMBEDDING_MODEL", "text-embedding-3-small")
    return AzureOpenAIEmbeddingModel(
        model=embedding_model,
        deployment_name=embedding_model,
        base_url=endpoint,
        api_key=api_key,
        api_version=api_version,
    )


def _load_context_paths() -> list[str]:
    paths = sorted(CONTEXTS_DIR.glob("*.txt"))
    if not paths:
        raise FileNotFoundError(f"No .txt files found in {CONTEXTS_DIR}")
    return [str(p) for p in paths]


def _goldens_to_preview(goldens) -> list[dict]:
    return [
        {
            "input": g.input,
            "expected_output": g.expected_output or "",
            "context": list(g.context or []),
            "retrieval_context": list(g.retrieval_context or []),
            "source_file": getattr(g, "source_file", ""),
        }
        for g in goldens
    ]


def main() -> None:
    context_paths = _load_context_paths()
    print(f"Found {len(context_paths)} context documents:")
    for p in context_paths:
        print(f"  {Path(p).name}")

    deployment = os.getenv("AZURE_CHAT_FLAG_MODEL", "gpt-4o")
    print(f"\nBuilding Azure OpenAI model ({deployment}) ...")
    model = _build_model()
    embedder = _build_embedder()

    print(
        f"Running Synthesizer — {MAX_GOLDENS_PER_DOC} goldens per doc "
        f"(~{MAX_GOLDENS_PER_DOC * len(context_paths)} total before curation) ...\n"
    )
    synthesizer = Synthesizer(model=model)
    context_config = ContextConstructionConfig(embedder=embedder, critic_model=model)
    synthesizer.generate_goldens_from_docs(
        document_paths=context_paths,
        include_expected_output=True,
        max_goldens_per_context=MAX_GOLDENS_PER_DOC,
        context_construction_config=context_config,
    )

    goldens = synthesizer.synthetic_goldens
    print(f"\nGenerated {len(goldens)} goldens.")

    EvaluationDataset(goldens=goldens).save_as(
        file_type="json",
        directory=str(OUTPUT_PATH.parent),
        file_name=OUTPUT_PATH.stem,
    )

    preview_path = OUTPUT_PATH.with_suffix(".preview.json")
    preview_path.write_text(
        json.dumps(_goldens_to_preview(goldens), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nSaved dataset  : {OUTPUT_PATH}")
    print(f"Human preview  : {preview_path}")
    print(
        "\nNext steps:\n"
        "  1. Open dataset.preview.json and remove low-quality or duplicate cases.\n"
        "  2. Re-save the curated list back to dataset.json for use in test_workflow.py.\n"
        "  3. Target: ~20 high-quality goldens covering all 5 agent domains."
    )


if __name__ == "__main__":
    main()