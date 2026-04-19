#!/usr/bin/env python3
"""Sentiment analysis tool using Hugging Face transformers (DistilBERT) with built-in fallback."""

import argparse
import csv
import json
import math
import os
import re
import sys
from pathlib import Path

DEFAULT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"


# ---------------------------------------------------------------------------
# Backend: Hugging Face transformers
# ---------------------------------------------------------------------------

def load_hf_pipeline(model_name):
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    from transformers import pipeline
    return pipeline(
        "sentiment-analysis",
        model=model_name,
        top_k=None,
        truncation=True,
    )


def analyze_hf(pipe, texts):
    raw_results = pipe(texts, batch_size=32)
    results = []
    for text, scores in zip(texts, raw_results):
        score_map = {s["label"]: s["score"] for s in scores}
        pos = score_map.get("POSITIVE", 0.0)
        neg = score_map.get("NEGATIVE", 0.0)
        compound = pos - neg
        if pos > neg:
            label = "POSITIVE"
        elif neg > pos:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"
        results.append({
            "text": _truncate(text),
            "label": label,
            "score": round(max(pos, neg), 4),
            "compound": round(compound, 4),
            "positive": round(pos, 4),
            "negative": round(neg, 4),
        })
    return results


# ---------------------------------------------------------------------------
# Backend: built-in lexicon (offline fallback)
# ---------------------------------------------------------------------------

_POS = {
    "good": 1.9, "great": 3.1, "excellent": 3.2, "amazing": 3.1, "wonderful": 2.8,
    "fantastic": 3.1, "awesome": 3.1, "outstanding": 3.2, "superb": 3.0, "brilliant": 3.0,
    "love": 3.2, "loved": 3.1, "loving": 2.8, "lovely": 2.6, "like": 1.5,
    "liked": 1.5, "enjoy": 2.0, "enjoyed": 2.0, "enjoying": 2.0, "enjoyable": 2.2,
    "happy": 2.7, "happiness": 2.8, "glad": 2.0, "pleased": 2.2, "delighted": 3.0,
    "thrilled": 3.0, "excited": 2.6, "exciting": 2.6, "enthusiasm": 2.5, "enthusiastic": 2.5,
    "perfect": 3.0, "best": 3.0, "beautiful": 2.8, "gorgeous": 2.8, "stunning": 2.8,
    "impressive": 2.5, "remarkable": 2.5, "incredible": 3.0, "magnificent": 3.0,
    "marvelous": 3.0, "terrific": 3.0, "splendid": 2.8, "fabulous": 3.0,
    "nice": 1.8, "fine": 1.3, "pleasant": 1.9, "cool": 1.8,
    "fun": 2.2, "funny": 2.0, "hilarious": 2.8, "entertaining": 2.2, "engaging": 2.0,
    "helpful": 2.0, "useful": 1.8, "valuable": 2.2, "worth": 1.5, "worthy": 1.8,
    "recommend": 2.2, "recommended": 2.2, "praise": 2.5, "praised": 2.5,
    "thank": 1.8, "thanks": 1.8, "thankful": 2.2, "grateful": 2.5, "appreciate": 2.2,
    "appreciated": 2.2, "positive": 1.8, "success": 2.5, "successful": 2.5,
    "win": 2.5, "winning": 2.5, "won": 2.5, "triumph": 2.8, "victory": 2.8,
    "easy": 1.5, "smooth": 1.8, "fast": 1.5, "efficient": 2.0, "effective": 2.0,
    "reliable": 2.0, "solid": 1.8, "strong": 1.8, "powerful": 2.0, "robust": 1.8,
    "innovative": 2.2, "creative": 2.0, "elegant": 2.5, "clean": 1.5, "fresh": 1.5,
    "warm": 1.5, "friendly": 2.0, "kind": 2.0, "generous": 2.2, "caring": 2.2,
    "comfortable": 1.8, "convenient": 1.8, "satisfying": 2.2, "satisfied": 2.2,
    "joy": 2.8, "joyful": 2.8, "cheerful": 2.2, "delight": 2.8,
    "hope": 1.8, "hopeful": 2.0, "promising": 2.0, "optimistic": 2.2,
    "safe": 1.5, "secure": 1.5, "trust": 2.0, "trusted": 2.0, "trustworthy": 2.2,
    "calm": 1.5, "peaceful": 2.0, "gentle": 1.5, "fair": 1.5, "smart": 2.0,
    "wise": 2.0, "insightful": 2.2, "inspired": 2.5, "inspiring": 2.5,
    "charming": 2.2, "adorable": 2.5, "cute": 2.0, "sweet": 2.0,
    "flawless": 3.0, "ideal": 2.5, "superior": 2.5, "premium": 2.0, "exceptional": 3.0,
    "phenomenal": 3.0, "glorious": 2.8, "divine": 2.8,
    "breathtaking": 3.0, "extraordinary": 3.0, "sensational": 3.0, "spectacular": 3.0,
    "wholesome": 2.2, "genuine": 1.8, "authentic": 1.8, "sincere": 2.0,
    "uplifting": 2.5, "heartwarming": 2.8, "touching": 2.2, "moving": 2.0,
    "refreshing": 2.0, "productive": 2.0, "prosperous": 2.5, "thriving": 2.5,
}

_NEG = {
    "bad": -2.5, "terrible": -3.2, "horrible": -3.2, "awful": -3.0, "dreadful": -3.0,
    "worst": -3.4, "worse": -2.5, "poor": -2.2, "pathetic": -2.8, "lousy": -2.5,
    "hate": -3.2, "hated": -3.1, "hating": -3.0, "hatred": -3.4, "loathe": -3.2,
    "despise": -3.2, "detest": -3.0, "dislike": -2.0, "disliked": -2.0,
    "angry": -2.5, "anger": -2.5, "furious": -3.0, "outraged": -3.0, "enraged": -3.0,
    "mad": -2.2, "irritated": -2.0, "annoyed": -2.0, "annoying": -2.2, "frustrated": -2.2,
    "frustrating": -2.5, "frustration": -2.5, "upset": -2.0, "agitated": -2.0,
    "sad": -2.2, "sadness": -2.2, "unhappy": -2.5, "depressed": -2.8, "depressing": -2.8,
    "miserable": -3.0, "gloomy": -2.0, "grief": -2.8, "sorrow": -2.5, "heartbroken": -3.0,
    "disappointed": -2.5, "disappointing": -2.8, "disappointment": -2.8,
    "disgusting": -3.0, "gross": -2.5, "revolting": -3.0, "nasty": -2.8, "vile": -3.0,
    "stupid": -2.5, "dumb": -2.2, "idiotic": -3.0, "foolish": -2.2,
    "ridiculous": -2.2, "absurd": -2.0, "nonsense": -2.0, "pointless": -2.2,
    "fail": -2.5, "failed": -2.5, "failure": -2.8, "failing": -2.5,
    "broken": -2.2, "crash": -2.2, "crashed": -2.5, "bug": -1.8,
    "error": -1.8, "wrong": -2.0, "mistake": -2.0, "fault": -1.8, "flawed": -2.2,
    "boring": -2.2, "bored": -2.0, "dull": -2.0, "tedious": -2.2, "monotonous": -2.2,
    "slow": -1.5, "sluggish": -1.8, "useless": -2.8, "worthless": -3.0,
    "waste": -2.2, "wasted": -2.2, "garbage": -2.8, "trash": -2.5, "junk": -2.2,
    "painful": -2.5, "pain": -2.0, "hurt": -2.2, "suffering": -2.5,
    "damage": -2.2, "damaged": -2.2, "harmful": -2.5, "dangerous": -2.5, "toxic": -2.8,
    "fear": -2.2, "scared": -2.2, "afraid": -2.2, "terrified": -3.0,
    "horrified": -3.0, "horrifying": -3.0, "scary": -2.2, "nightmare": -3.0,
    "weak": -1.8, "unstable": -2.0, "unreliable": -2.2,
    "cheap": -1.5, "inferior": -2.2, "mediocre": -1.8, "subpar": -2.0,
    "rude": -2.5, "cruel": -3.0, "selfish": -2.2, "hostile": -2.5,
    "aggressive": -2.0, "violent": -2.8, "harsh": -2.0, "brutal": -2.8,
    "negative": -1.8, "problem": -1.5, "problems": -1.8, "issue": -1.3, "issues": -1.5,
    "trouble": -1.8, "difficult": -1.5, "complicated": -1.3,
    "impossible": -2.2, "hopeless": -2.8, "helpless": -2.5, "desperate": -2.5,
    "lonely": -2.2, "abandoned": -2.5, "neglected": -2.2,
    "rejected": -2.5, "rejection": -2.5, "loss": -2.0, "lost": -1.8,
    "stress": -2.0, "stressed": -2.0, "anxiety": -2.2, "anxious": -2.0,
    "panic": -2.5, "worried": -1.8, "nervous": -1.8,
    "confusing": -1.8, "confused": -1.5, "chaos": -2.2, "mess": -2.0,
    "disaster": -3.0, "catastrophe": -3.2, "tragic": -2.8, "tragedy": -2.8,
    "destroyed": -2.8, "destruction": -2.8, "ruin": -2.5, "ruined": -2.8,
    "scam": -3.0, "fraud": -3.0, "fake": -2.5, "lie": -2.5, "lies": -2.5, "liar": -3.0,
    "betrayed": -3.0, "betrayal": -3.2, "cheat": -2.8, "cheated": -2.8,
    "corrupt": -2.8, "evil": -3.0, "malicious": -2.8,
    "abysmal": -3.2, "atrocious": -3.2, "appalling": -3.0,
    "intolerable": -2.8, "unbearable": -2.8, "unacceptable": -2.5,
    "offensive": -2.5, "insulting": -2.5, "humiliating": -2.8,
    "shameful": -2.5, "embarrassing": -2.0,
}

_NEGATIONS = {
    "not", "no", "never", "neither", "nobody", "nothing", "nowhere",
    "nor", "cannot", "can't", "won't", "don't", "doesn't", "didn't",
    "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't",
    "hadn't", "wouldn't", "shouldn't", "couldn't", "barely", "hardly",
    "scarcely", "seldom", "rarely",
}

_BOOSTERS = {
    "very": 1.5, "really": 1.4, "extremely": 1.8, "incredibly": 1.7,
    "absolutely": 1.6, "completely": 1.5, "totally": 1.5, "utterly": 1.6,
    "highly": 1.4, "deeply": 1.4, "truly": 1.4, "remarkably": 1.5,
    "so": 1.3, "super": 1.5, "especially": 1.4, "particularly": 1.3,
    "exceptionally": 1.6, "enormously": 1.6, "immensely": 1.6,
    "most": 1.4, "quite": 1.2, "rather": 1.1, "fairly": 1.1,
}

_BUT = {"but", "however", "yet", "although", "though", "nevertheless", "nonetheless", "except"}


def _tokenize(text):
    text = text.lower().strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", "", text)
    return re.findall(r"\b[\w']+\b|[!?]+", text)


def _word_score(w):
    return _POS.get(w, _NEG.get(w, 0.0))


def _analyze_lexicon(text):
    tokens = _tokenize(text)
    if not tokens:
        return {"text": _truncate(text), "label": "NEUTRAL", "score": 1.0,
                "compound": 0.0, "positive": 0.0, "negative": 0.0}

    raw = []
    neg_active = False
    boost = 1.0
    for tok in tokens:
        if tok in _NEGATIONS:
            neg_active = True
            continue
        if tok in _BOOSTERS:
            boost = _BOOSTERS[tok]
            continue
        s = _word_score(tok)
        if s != 0.0:
            s *= boost
            if neg_active:
                s *= -0.75
            raw.append(s)
        if tok not in _BOOSTERS:
            neg_active = False
            boost = 1.0

    # but-clause weighting
    but_idx = next((i for i, t in enumerate(tokens) if t in _BUT), None)
    if but_idx is not None and raw:
        positions = [i for i, t in enumerate(tokens) if _word_score(t) != 0.0]
        raw = [s * (0.5 if si < len(positions) and positions[si] < but_idx else 1.5)
               for si, s in enumerate(raw)]

    pos_sum = sum(s for s in raw if s > 0)
    neg_sum = abs(sum(s for s in raw if s < 0))
    total = pos_sum + neg_sum

    if total == 0:
        return {"text": _truncate(text), "label": "NEUTRAL", "score": 1.0,
                "compound": 0.0, "positive": 0.0, "negative": 0.0}

    pos_p = pos_sum / (total + 1e-6)
    neg_p = neg_sum / (total + 1e-6)
    compound_raw = sum(raw)
    compound = compound_raw / math.sqrt(compound_raw ** 2 + 15)

    if compound >= 0.05:
        label = "POSITIVE"
        score = round(0.5 + compound * 0.5, 4)
    elif compound <= -0.05:
        label = "NEGATIVE"
        score = round(0.5 + abs(compound) * 0.5, 4)
    else:
        label = "NEUTRAL"
        score = round(1.0 - abs(compound) * 10, 4)

    return {
        "text": _truncate(text),
        "label": label,
        "score": max(0.5, min(1.0, score)),
        "compound": round(compound, 4),
        "positive": round(pos_p, 4),
        "negative": round(neg_p, 4),
    }


def analyze_lexicon_batch(texts):
    return [_analyze_lexicon(t) for t in texts]


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _truncate(text, limit=200):
    return text[:limit] + ("..." if len(text) > limit else "")


def read_file_texts(filepath, column=None, field=None):
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    suffix = path.suffix.lower()

    if suffix == ".csv":
        texts = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if column is None:
                cols = reader.fieldnames or []
                if not cols:
                    print("Error: CSV file has no columns", file=sys.stderr)
                    sys.exit(1)
                column = cols[0]
                print(f"No --column specified, using first column: '{column}'", file=sys.stderr)
            for row in reader:
                if column in row and row[column].strip():
                    texts.append(row[column].strip())
        if not texts:
            print(f"Error: No text found in column '{column}'", file=sys.stderr)
            sys.exit(1)
        return texts

    if suffix == ".json":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, list):
            if field:
                return [str(item.get(field, "")).strip() for item in data
                        if isinstance(item, dict) and item.get(field)]
            return [str(item).strip() for item in data if str(item).strip()]
        elif isinstance(data, dict):
            if field and field in data:
                val = data[field]
                if isinstance(val, list):
                    return [str(v).strip() for v in val if str(v).strip()]
                return [str(val).strip()]
            return [json.dumps(data)]
        return [str(data)]

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines:
        print("Error: File is empty", file=sys.stderr)
        sys.exit(1)
    return lines


def format_output(results, output_format, backend_name):
    if output_format == "json":
        envelope = {"backend": backend_name, "results": results}
        print(json.dumps(envelope, indent=2, ensure_ascii=False))
    elif output_format == "csv":
        if not results:
            return
        fields = ["text", "label", "score", "compound", "positive", "negative"]
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    else:
        print(f"[backend: {backend_name}]\n")
        for i, r in enumerate(results):
            if len(results) > 1:
                print(f"--- Text {i + 1} ---")
            print(f"Text:     {r['text']}")
            print(f"Label:    {r['label']}")
            print(f"Score:    {r['score']}")
            print(f"Compound: {r['compound']}")
            print(f"Positive: {r['positive']}")
            print(f"Negative: {r['negative']}")
            if i < len(results) - 1:
                print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze text sentiment using Hugging Face transformers (DistilBERT). "
                    "Falls back to a built-in lexicon engine when transformers is unavailable.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --text "I love this product!"
  %(prog)s --text "Great!" --text "Terrible." --text "Okay."
  %(prog)s --file reviews.txt
  %(prog)s --file data.csv --column review_text
  %(prog)s --file data.json --field comment
  %(prog)s --file input.txt --output-format csv
  %(prog)s --model nlptown/bert-base-multilingual-uncased-sentiment --text "J'adore!"
  %(prog)s --backend lexicon --text "Fallback mode works offline"
        """,
    )
    parser.add_argument("--text", "-t", action="append",
                        help="Text to analyze (can be specified multiple times)")
    parser.add_argument("--file", "-f", help="Path to input file (TXT, CSV, or JSON)")
    parser.add_argument("--column", "-c", help="Column name for CSV files (defaults to first column)")
    parser.add_argument("--field", help="Field name for JSON files")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL,
                        help=f"Hugging Face model (default: {DEFAULT_MODEL})")
    parser.add_argument("--backend", "-b", choices=["auto", "transformers", "lexicon"],
                        default="auto",
                        help="Analysis backend: auto (try transformers, fall back to lexicon), "
                             "transformers (require HF), or lexicon (offline). Default: auto")
    parser.add_argument("--output-format", "-o", choices=["json", "csv", "text"],
                        default="json", help="Output format (default: json)")

    args = parser.parse_args()

    if not args.text and not args.file:
        if not sys.stdin.isatty():
            texts = [line.strip() for line in sys.stdin if line.strip()]
        else:
            parser.print_help()
            sys.exit(1)
    elif args.file:
        texts = read_file_texts(args.file, column=args.column, field=args.field)
    else:
        texts = args.text

    backend_name = None
    results = None

    if args.backend in ("auto", "transformers"):
        try:
            pipe = load_hf_pipeline(args.model)
            results = analyze_hf(pipe, texts)
            backend_name = f"transformers ({args.model})"
        except Exception as exc:
            if args.backend == "transformers":
                print(f"Error: transformers backend failed: {exc}", file=sys.stderr)
                sys.exit(1)
            print(f"Note: transformers unavailable ({type(exc).__name__}), using lexicon fallback.",
                  file=sys.stderr)

    if results is None:
        results = analyze_lexicon_batch(texts)
        backend_name = "lexicon (offline)"

    format_output(results, args.output_format, backend_name)


if __name__ == "__main__":
    main()
