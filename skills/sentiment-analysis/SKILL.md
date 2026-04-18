---
name: sentiment-analysis
description: Analyze text for emotional sentiment (positive, negative, neutral) using Hugging Face transformers and DistilBERT. Use when the user asks to analyze sentiment, tone, or emotional valence of text, reviews, feedback, survey responses, social media posts, or any written content. Supports single text analysis, batch processing of multiple texts, and file-based input (CSV, TXT, JSON). Supports custom HF models.
---

# Sentiment Analysis Tool

Analyze text sentiment using Hugging Face's `transformers` library with a pre-trained DistilBERT model (`distilbert-base-uncased-finetuned-sst-2-english`). Falls back to a built-in lexicon engine when transformers is unavailable.

**For HF backend**: `pip install transformers torch`
**Lexicon backend**: No dependencies (works offline)

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

# Use a different Hugging Face model
python scripts/analyze_sentiment.py --model nlptown/bert-base-multilingual-uncased-sentiment --text "J'adore ce produit!"

# Force lexicon backend (no dependencies, works offline)
python scripts/analyze_sentiment.py --backend lexicon --text "Works anywhere"

# Force transformers backend (fails if HF unavailable)
python scripts/analyze_sentiment.py --backend transformers --text "Require HF"
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
    ├─ JSON (default) → --output-format json
    ├─ CSV → --output-format csv
    └─ Human-readable → --output-format text

Need a different language or domain?
    └─ Use --model <huggingface-model-id>

Backend?
    ├─ auto (default) → Tries transformers, falls back to lexicon
    ├─ transformers → Requires HF + torch installed
    └─ lexicon → Offline, no dependencies
```

## Output Format

Each analyzed text produces:
- **label**: Overall sentiment classification (`positive`, `negative`, `neutral`)
- **score**: Model confidence for the winning label (0.0 to 1.0)
- **compound**: Directional score from -1.0 (most negative) to +1.0 (most positive)
- **positive**: Probability of positive sentiment (0.0 to 1.0)
- **negative**: Probability of negative sentiment (0.0 to 1.0)

## Recommended Models

| Model | Use Case |
|-------|----------|
| `distilbert-base-uncased-finetuned-sst-2-english` (default) | General English sentiment, fast |
| `nlptown/bert-base-multilingual-uncased-sentiment` | Multilingual, 1-5 star ratings |
| `cardiffnlp/twitter-roberta-base-sentiment-latest` | Social media / tweets |
| `siebert/sentiment-roberta-large-english` | High-accuracy English |

## Backends

| Backend | Accuracy | Speed | Dependencies | Offline |
|---------|----------|-------|--------------|---------|
| `transformers` (default) | High (DistilBERT) | ~0.5s/text | transformers, torch | No (first run) |
| `lexicon` | Good (rule-based) | Instant | None | Yes |

The `auto` backend (default) tries transformers first and falls back to lexicon if unavailable.

## MCP Server (for Claude.ai)

To use this tool directly from Claude.ai, run the MCP server locally and connect it via Claude Desktop settings.

**Install deps and start the server:**
```bash
pip install -r mcp/requirements.txt
python mcp/server.py
```

**Add to Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "sentiment-analysis": {
      "command": "python",
      "args": ["/absolute/path/to/skills/sentiment-analysis/mcp/server.py"]
    }
  }
}
```

**Tools exposed:**
- `analyze_sentiment(text, model?, backend?)` — analyze a single text
- `analyze_sentiment_batch(texts, model?, backend?)` — analyze a list, returns results + summary counts

## Best Practices

- **First run**: The model downloads on first use (~250MB for DistilBERT). Subsequent runs use the cache
- **Batch processing**: For large datasets, use file-based input — the script processes in batches of 32 for efficiency
- **Truncation**: Texts longer than the model's max token length (512 tokens) are automatically truncated
- **Custom models**: Any Hugging Face `text-classification` model works with `--model`. Check the [Hugging Face Hub](https://huggingface.co/models?pipeline_tag=text-classification) for options
- **Offline use**: Use `--backend lexicon` when no internet or HF dependencies are available
