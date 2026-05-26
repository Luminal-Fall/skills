import csv
import io
import json
import sys
from unittest.mock import patch

import pytest
from analyze_sentiment import (
    _analyze_lexicon,
    analyze_lexicon_batch,
    format_output,
)


class TestLexiconBasicSentiment:
    def test_positive_word_gives_positive_label(self):
        result = _analyze_lexicon("excellent")
        assert result["label"] == "POSITIVE"
        assert result["compound"] > 0

    def test_negative_word_gives_negative_label(self):
        result = _analyze_lexicon("terrible")
        assert result["label"] == "NEGATIVE"
        assert result["compound"] < 0

    def test_neutral_unknown_words_give_neutral_label(self):
        result = _analyze_lexicon("xyzzy frobbing qux")
        assert result["label"] == "NEUTRAL"
        assert result["compound"] == 0.0

    def test_empty_string_returns_neutral_with_full_score(self):
        result = _analyze_lexicon("")
        assert result["label"] == "NEUTRAL"
        assert result["score"] == 1.0
        assert result["compound"] == 0.0

    def test_whitespace_only_returns_neutral(self):
        result = _analyze_lexicon("   ")
        assert result["label"] == "NEUTRAL"
        assert result["compound"] == 0.0

    def test_result_contains_all_required_keys(self):
        result = _analyze_lexicon("good")
        for key in ("text", "label", "score", "compound", "positive", "negative"):
            assert key in result


class TestNegation:
    def test_negated_positive_word_becomes_negative(self):
        positive = _analyze_lexicon("I like this")
        negated = _analyze_lexicon("I don't like this")
        assert positive["compound"] > 0
        assert negated["compound"] < 0

    def test_negation_applies_minus_75_percent_multiplier(self):
        # "like" has score 1.5; negated → 1.5 * -0.75 = -1.125
        result = _analyze_lexicon("don't like")
        assert result["compound"] < 0

    def test_negation_resets_after_sentiment_word(self):
        # "not bad good": "not" negates "bad" (-2.5*-0.75=+1.875), then
        # negation resets, "good" is scored normally (+1.9)
        result = _analyze_lexicon("not bad good")
        assert result["compound"] > 0

    def test_negated_negative_word_becomes_positive(self):
        result = _analyze_lexicon("not terrible")
        assert result["compound"] > 0


class TestBoosters:
    def test_booster_increases_positive_compound(self):
        base = _analyze_lexicon("good")
        boosted = _analyze_lexicon("very good")
        assert boosted["compound"] > base["compound"]

    def test_stronger_booster_gives_higher_score(self):
        # "extremely" (1.8) > "very" (1.5) > "quite" (1.2)
        result_extreme = _analyze_lexicon("extremely good")
        result_very = _analyze_lexicon("very good")
        result_quite = _analyze_lexicon("quite good")
        assert result_extreme["compound"] > result_very["compound"]
        assert result_very["compound"] > result_quite["compound"]

    def test_booster_on_negative_amplifies_negativity(self):
        base = _analyze_lexicon("bad")
        boosted = _analyze_lexicon("very bad")
        assert boosted["compound"] < base["compound"]


class TestButClause:
    def test_but_shifts_weight_to_post_clause(self):
        # "terrible but excellent" → post-"but" (excellent) gets 1.5x weight
        result = _analyze_lexicon("terrible but excellent")
        assert result["label"] == "POSITIVE"

    def test_but_reduces_pre_clause_weight(self):
        # Without "but": compound dominated by pre-clause
        no_but = _analyze_lexicon("excellent terrible")
        with_but = _analyze_lexicon("excellent but terrible")
        # After "but", "terrible" gets 1.5x weight, making it more negative
        assert with_but["compound"] < no_but["compound"]

    def test_however_treated_as_but(self):
        result = _analyze_lexicon("bad however great")
        assert result["label"] == "POSITIVE"


class TestCompoundNormalization:
    def test_compound_is_in_minus_one_to_one_range(self):
        test_texts = [
            "absolutely wonderful amazing fantastic excellent",
            "horrible terrible awful disgusting",
            "okay",
            "not bad but not great either",
        ]
        for text in test_texts:
            result = _analyze_lexicon(text)
            assert -1.0 <= result["compound"] <= 1.0, (
                f"Compound out of range for '{text}': {result['compound']}"
            )

    def test_score_is_in_half_to_one_range(self):
        for text in ["great", "awful", "neither good nor bad really"]:
            result = _analyze_lexicon(text)
            assert 0.5 <= result["score"] <= 1.0, (
                f"Score out of range for '{text}': {result['score']}"
            )

    def test_positive_and_negative_ratios_sum_to_one(self):
        result = _analyze_lexicon("good and bad")
        assert result["positive"] + result["negative"] == pytest.approx(1.0, abs=1e-4)

    def test_purely_positive_text_has_zero_negative_ratio(self):
        result = _analyze_lexicon("excellent")
        assert result["negative"] == pytest.approx(0.0, abs=1e-4)

    def test_purely_negative_text_has_zero_positive_ratio(self):
        result = _analyze_lexicon("terrible")
        assert result["positive"] == pytest.approx(0.0, abs=1e-4)


class TestAnalyzeLexiconBatch:
    def test_returns_list_of_same_length(self):
        texts = ["great", "awful", ""]
        results = analyze_lexicon_batch(texts)
        assert len(results) == 3

    def test_each_result_has_correct_label(self):
        results = analyze_lexicon_batch(["good", "bad"])
        assert results[0]["label"] == "POSITIVE"
        assert results[1]["label"] == "NEGATIVE"

    def test_empty_list_returns_empty_list(self):
        assert analyze_lexicon_batch([]) == []


class TestFormatOutput:
    def _capture_json(self, results):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            format_output(results, "json", "lexicon")
            return json.loads(mock_stdout.getvalue())

    def _capture_csv(self, results):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            format_output(results, "csv", "lexicon")
            return mock_stdout.getvalue()

    def _capture_text(self, results):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            format_output(results, "text", "lexicon")
            return mock_stdout.getvalue()

    def _sample_result(self):
        return [{
            "text": "Hello",
            "label": "POSITIVE",
            "score": 0.75,
            "compound": 0.5,
            "positive": 1.0,
            "negative": 0.0,
        }]

    def test_json_output_is_valid_json(self):
        data = self._capture_json(self._sample_result())
        assert "results" in data
        assert "backend" in data

    def test_json_output_contains_results(self):
        data = self._capture_json(self._sample_result())
        assert len(data["results"]) == 1
        assert data["results"][0]["label"] == "POSITIVE"

    def test_csv_output_has_correct_headers(self):
        csv_text = self._capture_csv(self._sample_result())
        reader = csv.DictReader(io.StringIO(csv_text))
        assert set(reader.fieldnames) >= {"text", "label", "score", "compound"}

    def test_csv_output_empty_results_produces_no_rows(self):
        csv_text = self._capture_csv([])
        assert csv_text == ""

    def test_text_output_contains_label(self):
        text = self._capture_text(self._sample_result())
        assert "POSITIVE" in text

    def test_text_output_contains_backend_name(self):
        text = self._capture_text(self._sample_result())
        assert "lexicon" in text
