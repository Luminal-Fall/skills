#!/usr/bin/env python3
"""MCP server exposing the sentiment analysis tool to Claude."""

import sys
from pathlib import Path

# Allow importing from the sibling scripts/ directory
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from mcp.server.fastmcp import FastMCP
from analyze_sentiment import (
    analyze_lexicon_batch,
    analyze_hf,
    load_hf_pipeline,
)

mcp = FastMCP("sentiment-analysis")

_hf_cache: dict = {}


def _get_pipeline(model: str):
    if model not in _hf_cache:
        _hf_cache[model] = load_hf_pipeline(model)
    return _hf_cache[model]


def _run(texts: list[str], model: str, backend: str) -> list[dict]:
    if backend == "lexicon":
        return analyze_lexicon_batch(texts)

    try:
        pipe = _get_pipeline(model)
        return analyze_hf(pipe, texts)
    except Exception as exc:
        if backend == "transformers":
            raise RuntimeError(f"Transformers backend failed: {exc}") from exc
        # auto: fall back to lexicon
        return analyze_lexicon_batch(texts)


DEFAULT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def analyze_sentiment(
    text: str,
    model: str = DEFAULT_MODEL,
    backend: str = "auto",
) -> dict:
    """Analyze the sentiment of a single piece of text.

    Returns a dict with:
    - label: POSITIVE, NEGATIVE, or NEUTRAL
    - score: confidence (0–1) for the winning label
    - compound: directional score from -1.0 to +1.0
    - positive: probability of positive sentiment
    - negative: probability of negative sentiment
    - backend: which engine was used

    Args:
        text: The text to analyze.
        model: Hugging Face model ID (default: distilbert-base-uncased-finetuned-sst-2-english).
        backend: "auto" (try HF, fall back to lexicon), "transformers", or "lexicon".
    """
    results = _run([text], model, backend)
    result = results[0]
    result["backend"] = (
        f"transformers ({model})" if "compound" in result and backend != "lexicon"
        else "lexicon (offline)"
    )
    return result


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def analyze_sentiment_batch(
    texts: list[str],
    model: str = DEFAULT_MODEL,
    backend: str = "auto",
) -> dict:
    """Analyze sentiment for a batch of texts in one call.

    Returns a dict with:
    - results: list of per-text sentiment dicts (label, score, compound, positive, negative)
    - backend: which engine was used
    - summary: counts of POSITIVE / NEGATIVE / NEUTRAL labels

    Args:
        texts: List of texts to analyze.
        model: Hugging Face model ID (default: distilbert-base-uncased-finetuned-sst-2-english).
        backend: "auto" (try HF, fall back to lexicon), "transformers", or "lexicon".
    """
    if not texts:
        return {"results": [], "backend": "n/a", "summary": {}}

    results = _run(texts, model, backend)

    summary: dict[str, int] = {}
    for r in results:
        summary[r["label"]] = summary.get(r["label"], 0) + 1

    backend_name = f"transformers ({model})" if backend != "lexicon" else "lexicon (offline)"

    return {
        "results": results,
        "backend": backend_name,
        "summary": summary,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
