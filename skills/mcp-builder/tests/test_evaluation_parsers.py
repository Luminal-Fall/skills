import textwrap
from pathlib import Path

import pytest
from evaluation import extract_xml_content, parse_evaluation_file, parse_env_vars, parse_headers


class TestExtractXmlContent:
    def test_extracts_content_between_tags(self):
        assert extract_xml_content("<response>hello</response>", "response") == "hello"

    def test_strips_surrounding_whitespace(self):
        assert extract_xml_content("<response>  world  </response>", "response") == "world"

    def test_returns_none_when_tag_absent(self):
        assert extract_xml_content("no tags here", "response") is None

    def test_multiline_content_preserved(self):
        text = "<summary>\nline one\nline two\n</summary>"
        result = extract_xml_content(text, "summary")
        assert "line one" in result
        assert "line two" in result

    def test_returns_last_match_for_multiple_same_tags(self):
        # Non-greedy regex returns last match; important for nested-like scenarios
        text = "<response>first</response> ... <response>last</response>"
        assert extract_xml_content(text, "response") == "last"

    def test_different_tag_names_do_not_cross_match(self):
        text = "<response>correct</response><feedback>wrong</feedback>"
        assert extract_xml_content(text, "response") == "correct"
        assert extract_xml_content(text, "feedback") == "wrong"

    def test_empty_tag_content_returns_empty_string(self):
        assert extract_xml_content("<response></response>", "response") == ""


class TestParseHeaders:
    def test_parses_key_value_pair(self):
        result = parse_headers(["Authorization: Bearer token"])
        assert result == {"Authorization": "Bearer token"}

    def test_parses_multiple_headers(self):
        result = parse_headers(["Content-Type: application/json", "X-Custom: value"])
        assert result["Content-Type"] == "application/json"
        assert result["X-Custom"] == "value"

    def test_value_with_colon_is_preserved(self):
        # Split on first colon only; "Bearer: tok:en" → key="Bearer", value=" tok:en"
        result = parse_headers(["Authorization: Bearer tok:en"])
        assert result["Authorization"] == "Bearer tok:en"

    def test_malformed_header_without_colon_is_skipped(self, capsys):
        result = parse_headers(["malformed-no-colon"])
        assert result == {}
        captured = capsys.readouterr()
        assert "malformed" in captured.out.lower() or "warning" in captured.out.lower()

    def test_empty_list_returns_empty_dict(self):
        assert parse_headers([]) == {}

    def test_none_returns_empty_dict(self):
        assert parse_headers(None) == {}

    def test_strips_whitespace_from_keys_and_values(self):
        result = parse_headers(["  Key  :  Value  "])
        assert result.get("Key") == "Value"


class TestParseEnvVars:
    def test_parses_key_value_pair(self):
        result = parse_env_vars(["KEY=VALUE"])
        assert result == {"KEY": "VALUE"}

    def test_parses_multiple_vars(self):
        result = parse_env_vars(["FOO=bar", "BAZ=qux"])
        assert result["FOO"] == "bar"
        assert result["BAZ"] == "qux"

    def test_value_with_equals_sign_is_preserved(self):
        # split("=", 1) → value contains embedded "="
        result = parse_env_vars(["DB_URL=postgres://user:pass@host/db?param=1"])
        assert result["DB_URL"] == "postgres://user:pass@host/db?param=1"

    def test_malformed_var_without_equals_is_skipped(self, capsys):
        result = parse_env_vars(["NOEQUALSIGN"])
        assert result == {}
        captured = capsys.readouterr()
        assert "warning" in captured.out.lower() or "malformed" in captured.out.lower()

    def test_empty_list_returns_empty_dict(self):
        assert parse_env_vars([]) == {}

    def test_none_returns_empty_dict(self):
        assert parse_env_vars(None) == {}


class TestParseEvaluationFile:
    def _write_eval_xml(self, tmp_path, content):
        f = tmp_path / "eval.xml"
        f.write_text(content, encoding="utf-8")
        return f

    def test_parses_single_qa_pair(self, tmp_path):
        xml = textwrap.dedent("""\
            <evaluations>
              <qa_pair>
                <question>What is 2+2?</question>
                <answer>4</answer>
              </qa_pair>
            </evaluations>
        """)
        result = parse_evaluation_file(self._write_eval_xml(tmp_path, xml))
        assert len(result) == 1
        assert result[0]["question"] == "What is 2+2?"
        assert result[0]["answer"] == "4"

    def test_parses_multiple_qa_pairs(self, tmp_path):
        xml = textwrap.dedent("""\
            <evaluations>
              <qa_pair>
                <question>Q1</question>
                <answer>A1</answer>
              </qa_pair>
              <qa_pair>
                <question>Q2</question>
                <answer>A2</answer>
              </qa_pair>
            </evaluations>
        """)
        result = parse_evaluation_file(self._write_eval_xml(tmp_path, xml))
        assert len(result) == 2
        assert result[1]["question"] == "Q2"

    def test_strips_whitespace_from_question_and_answer(self, tmp_path):
        xml = textwrap.dedent("""\
            <evaluations>
              <qa_pair>
                <question>  How many?  </question>
                <answer>  42  </answer>
              </qa_pair>
            </evaluations>
        """)
        result = parse_evaluation_file(self._write_eval_xml(tmp_path, xml))
        assert result[0]["question"] == "How many?"
        assert result[0]["answer"] == "42"

    def test_skips_qa_pairs_missing_question_or_answer(self, tmp_path):
        xml = textwrap.dedent("""\
            <evaluations>
              <qa_pair>
                <question>Q only</question>
              </qa_pair>
              <qa_pair>
                <question>Complete</question>
                <answer>Yes</answer>
              </qa_pair>
            </evaluations>
        """)
        result = parse_evaluation_file(self._write_eval_xml(tmp_path, xml))
        assert len(result) == 1
        assert result[0]["question"] == "Complete"

    def test_returns_empty_list_for_malformed_xml(self, tmp_path):
        bad = tmp_path / "bad.xml"
        bad.write_text("<unclosed", encoding="utf-8")
        result = parse_evaluation_file(bad)
        assert result == []

    def test_returns_empty_list_for_nonexistent_file(self, tmp_path):
        result = parse_evaluation_file(tmp_path / "ghost.xml")
        assert result == []
