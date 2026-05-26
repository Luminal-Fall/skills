"""Tests for merge_runs.py — DOCX run consolidation logic."""

import textwrap
from pathlib import Path

import pytest

defusedxml = pytest.importorskip("defusedxml", reason="defusedxml not installed")
import defusedxml.minidom

from merge_runs import (
    _can_merge,
    _find_elements,
    _get_child,
    _is_adjacent,
    _is_run,
    merge_runs,
)

W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _parse(xml_str: str):
    return defusedxml.minidom.parseString(xml_str.encode("utf-8"))


def _make_doc(body_content: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document {W_NS}>'
        f"<w:body>{body_content}</w:body>"
        f"</w:document>"
    )


def _write_doc(tmp_path: Path, body_content: str) -> Path:
    word_dir = tmp_path / "word"
    word_dir.mkdir()
    doc = word_dir / "document.xml"
    doc.write_text(_make_doc(body_content), encoding="utf-8")
    return tmp_path


def _get_runs(doc_xml: Path) -> list:
    dom = defusedxml.minidom.parseString(doc_xml.read_bytes())
    return _find_elements(dom.documentElement, "r")


def _get_text_content(doc_xml: Path) -> str:
    dom = defusedxml.minidom.parseString(doc_xml.read_bytes())
    texts = _find_elements(dom.documentElement, "t")
    return "".join(
        t.firstChild.data for t in texts if t.firstChild
    )


class TestFindElements:
    def test_finds_namespaced_elements(self):
        dom = _parse(_make_doc("<w:p><w:r><w:t>hi</w:t></w:r></w:p>"))
        runs = _find_elements(dom.documentElement, "r")
        assert len(runs) == 1

    def test_finds_deeply_nested_elements(self):
        dom = _parse(_make_doc("<w:p><w:ins><w:r><w:t>a</w:t></w:r></w:ins></w:p>"))
        runs = _find_elements(dom.documentElement, "r")
        assert len(runs) == 1

    def test_returns_empty_list_when_not_found(self):
        dom = _parse(_make_doc("<w:p/>"))
        assert _find_elements(dom.documentElement, "r") == []


class TestIsRun:
    def test_namespaced_r_element_is_run(self):
        dom = _parse(_make_doc("<w:p><w:r/></w:p>"))
        runs = _find_elements(dom.documentElement, "r")
        assert _is_run(runs[0])

    def test_non_run_element_is_not_run(self):
        dom = _parse(_make_doc("<w:p><w:t>hi</w:t></w:p>"))
        ts = _find_elements(dom.documentElement, "t")
        assert not _is_run(ts[0])


class TestIsAdjacent:
    def test_directly_adjacent_elements_are_adjacent(self):
        dom = _parse(_make_doc("<w:p><w:t>a</w:t><w:t>b</w:t></w:p>"))
        ts = _find_elements(dom.documentElement, "t")
        assert _is_adjacent(ts[0], ts[1])

    def test_whitespace_text_node_between_is_adjacent(self):
        # Newline/space between elements counts as whitespace-only text → still adjacent
        dom = _parse(
            _make_doc("<w:p><w:t>a</w:t>  \n  <w:t>b</w:t></w:p>")
        )
        ts = _find_elements(dom.documentElement, "t")
        assert _is_adjacent(ts[0], ts[1])

    def test_element_node_between_is_not_adjacent(self):
        dom = _parse(_make_doc("<w:p><w:t>a</w:t><w:r/><w:t>b</w:t></w:p>"))
        ts = _find_elements(dom.documentElement, "t")
        assert not _is_adjacent(ts[0], ts[1])

    def test_non_whitespace_text_between_is_not_adjacent(self):
        dom = _parse(_make_doc("<w:p><w:t>a</w:t>SURPRISE<w:t>b</w:t></w:p>"))
        ts = _find_elements(dom.documentElement, "t")
        assert not _is_adjacent(ts[0], ts[1])


class TestCanMerge:
    def test_runs_without_rpr_can_merge(self):
        dom = _parse(_make_doc("<w:p><w:r/><w:r/></w:p>"))
        runs = _find_elements(dom.documentElement, "r")
        assert _can_merge(runs[0], runs[1])

    def test_runs_with_identical_rpr_can_merge(self):
        xml = _make_doc(
            "<w:p>"
            "<w:r><w:rPr><w:b/></w:rPr><w:t>a</w:t></w:r>"
            "<w:r><w:rPr><w:b/></w:rPr><w:t>b</w:t></w:r>"
            "</w:p>"
        )
        dom = _parse(xml)
        runs = _find_elements(dom.documentElement, "r")
        assert _can_merge(runs[0], runs[1])

    def test_runs_with_different_rpr_cannot_merge(self):
        xml = _make_doc(
            "<w:p>"
            "<w:r><w:rPr><w:b/></w:rPr><w:t>bold</w:t></w:r>"
            "<w:r><w:rPr><w:i/></w:rPr><w:t>italic</w:t></w:r>"
            "</w:p>"
        )
        dom = _parse(xml)
        runs = _find_elements(dom.documentElement, "r")
        assert not _can_merge(runs[0], runs[1])

    def test_run_with_rpr_and_without_cannot_merge(self):
        xml = _make_doc(
            "<w:p>"
            "<w:r><w:rPr><w:b/></w:rPr><w:t>bold</w:t></w:r>"
            "<w:r><w:t>plain</w:t></w:r>"
            "</w:p>"
        )
        dom = _parse(xml)
        runs = _find_elements(dom.documentElement, "r")
        assert not _can_merge(runs[0], runs[1])


class TestMergeRunsIntegration:
    def test_two_plain_runs_merge_into_one(self, tmp_path):
        _write_doc(
            tmp_path,
            "<w:p><w:r><w:t>Hello</w:t></w:r><w:r><w:t>World</w:t></w:r></w:p>",
        )
        count, msg = merge_runs(str(tmp_path))
        assert count == 1
        runs = _get_runs(tmp_path / "word" / "document.xml")
        assert len(runs) == 1

    def test_merged_run_has_concatenated_text(self, tmp_path):
        _write_doc(
            tmp_path,
            "<w:p><w:r><w:t>Hello</w:t></w:r><w:r><w:t>World</w:t></w:r></w:p>",
        )
        merge_runs(str(tmp_path))
        assert _get_text_content(tmp_path / "word" / "document.xml") == "HelloWorld"

    def test_runs_with_different_rpr_are_not_merged(self, tmp_path):
        _write_doc(
            tmp_path,
            "<w:p>"
            "<w:r><w:rPr><w:b/></w:rPr><w:t>Bold</w:t></w:r>"
            "<w:r><w:rPr><w:i/></w:rPr><w:t>Italic</w:t></w:r>"
            "</w:p>",
        )
        count, _ = merge_runs(str(tmp_path))
        assert count == 0
        assert len(_get_runs(tmp_path / "word" / "document.xml")) == 2

    def test_proof_err_elements_removed_before_merge(self, tmp_path):
        # proofErr between runs should be removed, allowing the merge
        _write_doc(
            tmp_path,
            "<w:p>"
            "<w:r><w:t>mis</w:t></w:r>"
            "<w:proofErr w:type='spellStart'/>"
            "<w:r><w:t>spelled</w:t></w:r>"
            "</w:p>",
        )
        merge_runs(str(tmp_path))
        dom = defusedxml.minidom.parseString(
            (tmp_path / "word" / "document.xml").read_bytes()
        )
        proof_errs = _find_elements(dom.documentElement, "proofErr")
        assert len(proof_errs) == 0

    def test_missing_document_xml_returns_error(self, tmp_path):
        count, msg = merge_runs(str(tmp_path))
        assert count == 0
        assert "error" in msg.lower()

    def test_text_with_leading_space_gets_preserve_attribute(self, tmp_path):
        # " Hello" + "World" → merged " HelloWorld" has leading space → needs preserve
        _write_doc(
            tmp_path,
            "<w:p>"
            "<w:r><w:t> Hello</w:t></w:r>"
            "<w:r><w:t>World</w:t></w:r>"
            "</w:p>",
        )
        merge_runs(str(tmp_path))
        dom = defusedxml.minidom.parseString(
            (tmp_path / "word" / "document.xml").read_bytes()
        )
        t_elements = _find_elements(dom.documentElement, "t")
        merged_t = t_elements[0]
        assert merged_t.getAttribute("xml:space") == "preserve"

    def test_three_mergeable_runs_merge_into_one(self, tmp_path):
        _write_doc(
            tmp_path,
            "<w:p>"
            "<w:r><w:t>a</w:t></w:r>"
            "<w:r><w:t>b</w:t></w:r>"
            "<w:r><w:t>c</w:t></w:r>"
            "</w:p>",
        )
        count, _ = merge_runs(str(tmp_path))
        assert count == 2
        assert len(_get_runs(tmp_path / "word" / "document.xml")) == 1
