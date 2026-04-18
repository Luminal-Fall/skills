#!/usr/bin/env python3
"""Sentiment analysis tool using a lexicon-based approach with no external dependencies."""

import argparse
import csv
import json
import math
import re
import sys
from io import StringIO
from pathlib import Path

# --- Lexicon ---

POSITIVE_WORDS = {
    "good": 1.9, "great": 3.1, "excellent": 3.2, "amazing": 3.1, "wonderful": 2.8,
    "fantastic": 3.1, "awesome": 3.1, "outstanding": 3.2, "superb": 3.0, "brilliant": 3.0,
    "love": 3.2, "loved": 3.1, "loving": 2.8, "lovely": 2.6, "like": 1.5,
    "liked": 1.5, "enjoy": 2.0, "enjoyed": 2.0, "enjoying": 2.0, "enjoyable": 2.2,
    "happy": 2.7, "happiness": 2.8, "glad": 2.0, "pleased": 2.2, "delighted": 3.0,
    "thrilled": 3.0, "excited": 2.6, "exciting": 2.6, "enthusiasm": 2.5, "enthusiastic": 2.5,
    "perfect": 3.0, "best": 3.0, "beautiful": 2.8, "gorgeous": 2.8, "stunning": 2.8,
    "impressive": 2.5, "remarkable": 2.5, "incredible": 3.0, "magnificent": 3.0,
    "marvelous": 3.0, "terrific": 3.0, "splendid": 2.8, "fabulous": 3.0,
    "nice": 1.8, "fine": 1.3, "pleasant": 1.9, "pretty": 1.5, "cool": 1.8,
    "fun": 2.2, "funny": 2.0, "hilarious": 2.8, "entertaining": 2.2, "engaging": 2.0,
    "helpful": 2.0, "useful": 1.8, "valuable": 2.2, "worth": 1.5, "worthy": 1.8,
    "recommend": 2.2, "recommended": 2.2, "praise": 2.5, "praised": 2.5,
    "thank": 1.8, "thanks": 1.8, "thankful": 2.2, "grateful": 2.5, "appreciate": 2.2,
    "appreciated": 2.2, "positive": 1.8, "success": 2.5, "successful": 2.5,
    "win": 2.5, "winning": 2.5, "won": 2.5, "triumph": 2.8, "victory": 2.8,
    "easy": 1.5, "simple": 1.0, "smooth": 1.8, "fast": 1.5, "quick": 1.3,
    "efficient": 2.0, "effective": 2.0, "reliable": 2.0, "solid": 1.8,
    "strong": 1.8, "powerful": 2.0, "robust": 1.8, "innovative": 2.2,
    "creative": 2.0, "elegant": 2.5, "clean": 1.5, "fresh": 1.5, "bright": 1.5,
    "warm": 1.5, "friendly": 2.0, "kind": 2.0, "generous": 2.2, "caring": 2.2,
    "comfortable": 1.8, "convenient": 1.8, "satisfying": 2.2, "satisfied": 2.2,
    "satisfaction": 2.2, "joy": 2.8, "joyful": 2.8, "cheerful": 2.2, "delight": 2.8,
    "hope": 1.8, "hopeful": 2.0, "promising": 2.0, "optimistic": 2.2,
    "safe": 1.5, "secure": 1.5, "trust": 2.0, "trusted": 2.0, "trustworthy": 2.2,
    "calm": 1.5, "peaceful": 2.0, "serene": 2.2, "gentle": 1.5, "pure": 1.5,
    "fair": 1.5, "balanced": 1.3, "reasonable": 1.3, "smart": 2.0, "clever": 1.8,
    "wise": 2.0, "insightful": 2.2, "inspired": 2.5, "inspiring": 2.5,
    "courageous": 2.5, "brave": 2.2, "hero": 2.5, "heroic": 2.5,
    "charming": 2.2, "adorable": 2.5, "cute": 2.0, "sweet": 2.0,
    "paradise": 3.0, "heavenly": 2.8, "blessed": 2.5, "magical": 2.5, "miracle": 3.0,
    "flawless": 3.0, "ideal": 2.5, "superior": 2.5, "premium": 2.0, "exceptional": 3.0,
    "phenomenal": 3.0, "glorious": 2.8, "graceful": 2.2, "divine": 2.8,
    "breathtaking": 3.0, "extraordinary": 3.0, "sensational": 3.0, "spectacular": 3.0,
    "radiant": 2.5, "vibrant": 2.2, "lively": 2.0, "energetic": 2.0,
    "wholesome": 2.2, "genuine": 1.8, "authentic": 1.8, "sincere": 2.0,
    "uplifting": 2.5, "heartwarming": 2.8, "touching": 2.2, "moving": 2.0,
    "refreshing": 2.0, "rejuvenating": 2.2, "invigorating": 2.2,
    "productive": 2.0, "prosperous": 2.5, "thriving": 2.5, "flourishing": 2.5,
}

NEGATIVE_WORDS = {
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
    "ugly": -2.5, "hideous": -3.0, "disgusting": -3.0, "gross": -2.5, "revolting": -3.0,
    "nasty": -2.8, "vile": -3.0, "repulsive": -3.0, "sickening": -2.8,
    "stupid": -2.5, "dumb": -2.2, "idiotic": -3.0, "foolish": -2.2, "moronic": -3.0,
    "ridiculous": -2.2, "absurd": -2.0, "nonsense": -2.0, "pointless": -2.2,
    "fail": -2.5, "failed": -2.5, "failure": -2.8, "failing": -2.5,
    "broken": -2.2, "broke": -1.8, "crash": -2.2, "crashed": -2.5, "bug": -1.8,
    "error": -1.8, "wrong": -2.0, "mistake": -2.0, "fault": -1.8, "flawed": -2.2,
    "boring": -2.2, "bored": -2.0, "dull": -2.0, "tedious": -2.2, "monotonous": -2.2,
    "slow": -1.5, "sluggish": -1.8, "lazy": -1.8, "useless": -2.8, "worthless": -3.0,
    "waste": -2.2, "wasted": -2.2, "wasteful": -2.2, "garbage": -2.8, "trash": -2.5,
    "junk": -2.2, "rubbish": -2.5, "crap": -2.8,
    "painful": -2.5, "pain": -2.0, "hurt": -2.2, "hurts": -2.2, "suffering": -2.5,
    "damage": -2.2, "damaged": -2.2, "harmful": -2.5, "dangerous": -2.5, "toxic": -2.8,
    "fear": -2.2, "scared": -2.2, "afraid": -2.2, "terrified": -3.0, "frightened": -2.5,
    "horrified": -3.0, "horrifying": -3.0, "scary": -2.2, "creepy": -2.0, "nightmare": -3.0,
    "weak": -1.8, "fragile": -1.5, "vulnerable": -1.5, "unstable": -2.0, "unreliable": -2.2,
    "cheap": -1.5, "inferior": -2.2, "mediocre": -1.8, "subpar": -2.0, "lackluster": -2.0,
    "rude": -2.5, "mean": -2.2, "cruel": -3.0, "selfish": -2.2, "greedy": -2.2,
    "hostile": -2.5, "aggressive": -2.0, "violent": -2.8, "harsh": -2.0, "brutal": -2.8,
    "negative": -1.8, "problem": -1.5, "problems": -1.8, "issue": -1.3, "issues": -1.5,
    "trouble": -1.8, "troubled": -2.0, "difficult": -1.5, "complicated": -1.3,
    "impossible": -2.2, "hopeless": -2.8, "helpless": -2.5, "desperate": -2.5,
    "sick": -1.8, "ill": -1.5, "disease": -2.0, "infection": -1.8,
    "lonely": -2.2, "alone": -1.5, "isolated": -1.8, "abandoned": -2.5, "neglected": -2.2,
    "reject": -2.2, "rejected": -2.5, "rejection": -2.5, "denied": -1.8,
    "loss": -2.0, "lost": -1.8, "lose": -2.0, "losing": -2.0,
    "stress": -2.0, "stressed": -2.0, "stressful": -2.2, "anxiety": -2.2, "anxious": -2.0,
    "panic": -2.5, "worried": -1.8, "worry": -1.8, "nervous": -1.8,
    "confusing": -1.8, "confused": -1.5, "chaos": -2.2, "chaotic": -2.2, "mess": -2.0,
    "disaster": -3.0, "catastrophe": -3.2, "tragic": -2.8, "tragedy": -2.8,
    "death": -2.5, "dead": -2.2, "die": -2.2, "dying": -2.5, "kill": -2.8,
    "destroyed": -2.8, "destruction": -2.8, "ruin": -2.5, "ruined": -2.8,
    "scam": -3.0, "fraud": -3.0, "fake": -2.5, "lie": -2.5, "lies": -2.5, "liar": -3.0,
    "betray": -3.0, "betrayed": -3.0, "betrayal": -3.2, "cheat": -2.8, "cheated": -2.8,
    "manipulate": -2.5, "corrupt": -2.8, "corruption": -2.8, "evil": -3.0,
    "wicked": -2.8, "sinister": -2.5, "malicious": -2.8,
    "abysmal": -3.2, "atrocious": -3.2, "appalling": -3.0, "ghastly": -2.8,
    "intolerable": -2.8, "unbearable": -2.8, "unacceptable": -2.5,
    "offensive": -2.5, "insulting": -2.5, "humiliating": -2.8, "degrading": -2.5,
    "shameful": -2.5, "embarrassing": -2.0, "awkward": -1.5, "cringe": -2.0,
}

NEGATION_WORDS = {
    "not", "no", "never", "neither", "nobody", "nothing", "nowhere",
    "nor", "cannot", "can't", "won't", "don't", "doesn't", "didn't",
    "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't",
    "hadn't", "wouldn't", "shouldn't", "couldn't", "barely", "hardly",
    "scarcely", "seldom", "rarely",
}

BOOSTERS = {
    "very": 1.5, "really": 1.4, "extremely": 1.8, "incredibly": 1.7,
    "absolutely": 1.6, "completely": 1.5, "totally": 1.5, "utterly": 1.6,
    "highly": 1.4, "deeply": 1.4, "truly": 1.4, "remarkably": 1.5,
    "so": 1.3, "super": 1.5, "especially": 1.4, "particularly": 1.3,
    "exceptionally": 1.6, "enormously": 1.6, "immensely": 1.6,
    "terrifically": 1.5, "amazingly": 1.6, "fantastically": 1.6,
    "most": 1.4, "quite": 1.2, "rather": 1.1, "fairly": 1.1,
}

DAMPENERS = {
    "slightly": 0.6, "somewhat": 0.7, "a bit": 0.7, "a little": 0.7,
    "kind of": 0.7, "sort of": 0.7, "mildly": 0.6, "marginally": 0.5,
    "partly": 0.7, "partially": 0.7, "almost": 0.8, "barely": 0.5,
}

BUT_WORDS = {"but", "however", "yet", "although", "though", "nevertheless", "nonetheless", "except"}


def tokenize(text):
    text = text.lower().strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", "", text)
    tokens = re.findall(r"\b[\w']+\b|[!?]+", text)
    return tokens


def get_word_score(word):
    if word in POSITIVE_WORDS:
        return POSITIVE_WORDS[word]
    if word in NEGATIVE_WORDS:
        return NEGATIVE_WORDS[word]
    return 0.0


def analyze_single(text, verbose=False):
    tokens = tokenize(text)
    if not tokens:
        return {
            "text": text,
            "label": "neutral",
            "compound": 0.0,
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
        }

    word_scores = []
    raw_scores = []
    i = 0
    negation_active = False
    booster = 1.0

    while i < len(tokens):
        token = tokens[i]

        if token in NEGATION_WORDS:
            negation_active = True
            i += 1
            continue

        if token in BOOSTERS:
            booster = BOOSTERS[token]
            i += 1
            continue

        dampener_match = False
        if i + 1 < len(tokens):
            bigram = token + " " + tokens[i + 1]
            if bigram in DAMPENERS:
                booster = DAMPENERS[bigram]
                i += 2
                dampener_match = True
                continue

        if token in DAMPENERS and not dampener_match:
            booster = DAMPENERS[token]
            i += 1
            continue

        score = get_word_score(token)

        if score != 0.0:
            score *= booster
            if negation_active:
                score *= -0.75
            raw_scores.append(score)
            if verbose:
                word_scores.append({"word": token, "score": round(score, 3)})

        excl_count = 0
        if token in ("!", "!!", "!!!", "?", "??", "???"):
            excl_count = len(token)

        if excl_count > 0 and raw_scores:
            amp = min(excl_count * 0.15, 0.6)
            last = raw_scores[-1]
            raw_scores[-1] = last + (amp if last > 0 else -amp)

        if token not in BOOSTERS and token not in DAMPENERS:
            negation_active = False
            booster = 1.0

        i += 1

    # Handle "but" clause weighting
    but_index = None
    for idx, token in enumerate(tokens):
        if token in BUT_WORDS:
            but_index = idx
            break

    if but_index is not None and raw_scores:
        token_positions = []
        ti = 0
        for idx, token in enumerate(tokens):
            s = get_word_score(token)
            if s != 0.0:
                token_positions.append(idx)
                ti += 1

        weighted_scores = []
        for si, score in enumerate(raw_scores):
            if si < len(token_positions):
                if token_positions[si] < but_index:
                    weighted_scores.append(score * 0.5)
                else:
                    weighted_scores.append(score * 1.5)
            else:
                weighted_scores.append(score)
        raw_scores = weighted_scores

    pos_sum = sum(s for s in raw_scores if s > 0)
    neg_sum = sum(s for s in raw_scores if s < 0)
    total = pos_sum + abs(neg_sum)

    if total == 0:
        pos_prop = 0.0
        neg_prop = 0.0
        neu_prop = 1.0
    else:
        pos_prop = pos_sum / (total + 1e-6)
        neg_prop = abs(neg_sum) / (total + 1e-6)
        scored_tokens = len(raw_scores)
        total_tokens = max(len(tokens), 1)
        neu_prop = max(0.0, 1.0 - (scored_tokens / total_tokens))

    compound_raw = sum(raw_scores)
    compound = compound_raw / math.sqrt(compound_raw ** 2 + 15)

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    elif pos_prop > 0.25 and neg_prop > 0.25:
        label = "mixed"
    else:
        label = "neutral"

    result = {
        "text": text[:200] + ("..." if len(text) > 200 else ""),
        "label": label,
        "compound": round(compound, 4),
        "positive": round(pos_prop, 4),
        "negative": round(neg_prop, 4),
        "neutral": round(neu_prop, 4),
    }

    if verbose and word_scores:
        result["word_scores"] = word_scores

    return result


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
                return [str(item.get(field, "")).strip() for item in data if isinstance(item, dict) and item.get(field)]
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


def format_output(results, output_format):
    if output_format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif output_format == "csv":
        if not results:
            return
        fields = ["text", "label", "compound", "positive", "negative", "neutral"]
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    else:
        for i, r in enumerate(results):
            if len(results) > 1:
                print(f"\n--- Text {i + 1} ---")
            print(f"Text:     {r['text']}")
            print(f"Label:    {r['label']}")
            print(f"Compound: {r['compound']}")
            print(f"Positive: {r['positive']}")
            print(f"Negative: {r['negative']}")
            print(f"Neutral:  {r['neutral']}")
            if "word_scores" in r:
                print("Word scores:")
                for ws in r["word_scores"]:
                    direction = "+" if ws["score"] > 0 else ""
                    print(f"  {ws['word']:20s} {direction}{ws['score']}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze text sentiment. Returns polarity scores and an overall label.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --text "I love this product!"
  %(prog)s --text "Great!" --text "Terrible." --text "Okay."
  %(prog)s --file reviews.txt
  %(prog)s --file data.csv --column review_text
  %(prog)s --file data.json --field comment
  %(prog)s --text "Absolutely wonderful experience" --verbose
  %(prog)s --file input.txt --output-format csv
        """,
    )
    parser.add_argument(
        "--text", "-t",
        action="append",
        help="Text to analyze (can be specified multiple times)",
    )
    parser.add_argument(
        "--file", "-f",
        help="Path to input file (TXT, CSV, or JSON)",
    )
    parser.add_argument(
        "--column", "-c",
        help="Column name for CSV files (defaults to first column)",
    )
    parser.add_argument(
        "--field",
        help="Field name for JSON files",
    )
    parser.add_argument(
        "--output-format", "-o",
        choices=["json", "csv", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-word sentiment scores",
    )

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

    results = [analyze_single(text, verbose=args.verbose) for text in texts]
    format_output(results, args.output_format)


if __name__ == "__main__":
    main()
