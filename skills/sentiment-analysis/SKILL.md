---
name: sentiment-analysis
description: Analyze text for emotional sentiment (positive, negative, neutral, mixed). Use when the user asks to analyze sentiment, tone, or emotional valence of text, reviews, feedback, survey responses, social media posts, or any written content. Supports single text analysis, batch processing of multiple texts, and file-based input (CSV, TXT, JSON).
---

# Sentiment Analysis Tool

Analyze text for sentiment polarity and emotional tone using a lexicon-based approach with no external API dependencies.

**Helper Scripts Available**:
- `scripts/analyze_sentiment.py` - Core sentiment analysis engine

**Always run scripts with `--help` first** to see usage. DO NOT read the source until you try running the script first. These scripts exist to be called directly as black-box scripts rather than ingested into your context window.

## Quick Start

```bash
# Analyze a single text
python scripts/analyze_sentiment.py --text "I love this product, it works great!"

# Analyze multiple texts
python scripts/analyze_sentiment.py --text "Great service!" --text "Terrible experience." --text "It was okay."

# Analyze a text file (one text per line)
python scripts/analyze_sentiment.py --file input.txt

# Analyze a CSV file (specify the text column)
python scripts/analyze_sentiment.py --file data.csv --column review_text

# Analyze a JSON file (specify the text field)
python scripts/analyze_sentiment.py --file data.json --field comment

# Output results as CSV
python scripts/analyze_sentiment.py --file input.txt --output-format csv

# Detailed breakdown with word-level scores
python scripts/analyze_sentiment.py --text "The movie was absolutely wonderful but the ending was disappointing" --verbose
```

## Decision Tree: Choosing Your Approach

```
User task → What kind of input?
    ├─ Single text string → Use --text "..."
    ├─ Multiple texts → Use multiple --text flags
    ├─ Text file (one per line) → Use --file input.txt
    ├─ CSV file → Use --file data.csv --column <column_name>
    └─ JSON file → Use --file data.json --field <field_name>

Output format needed?
    ├─ Human-readable (default) → No extra flags
    ├─ JSON → --output-format json (default)
    ├─ CSV → --output-format csv
    └─ Detailed breakdown → Add --verbose
```

## Output Format

Each analyzed text produces:
- **label**: Overall sentiment classification (`positive`, `negative`, `neutral`, `mixed`)
- **compound**: Normalized compound score from -1.0 (most negative) to +1.0 (most positive)
- **positive**: Proportion of positive sentiment (0.0 to 1.0)
- **negative**: Proportion of negative sentiment (0.0 to 1.0)
- **neutral**: Proportion of neutral sentiment (0.0 to 1.0)

With `--verbose`, you also get:
- **word_scores**: Per-word sentiment contributions

## Thresholds

| Compound Score | Label    |
|----------------|----------|
| >= 0.05        | positive |
| <= -0.05       | negative |
| both pos & neg > 0.25 | mixed |
| else           | neutral  |

## Best Practices

- **Preprocessing**: The script handles basic text normalization, but for best results provide clean text without HTML tags or excessive special characters
- **Batch processing**: For large datasets, use file-based input rather than multiple `--text` flags
- **Context**: The lexicon approach works well for reviews, social media, and general text. It may be less accurate for domain-specific jargon or sarcasm
- **Verbose mode**: Use `--verbose` when you need to understand which specific words are driving the sentiment score
