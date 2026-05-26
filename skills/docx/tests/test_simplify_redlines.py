"""Tests for simplify_redlines.py — tracked change merging logic."""

import io
import zipfile
from pathlib import Path

import pytest

defusedxml = pytest.importorskip("defusedxml", reason="defusedxml not installed")
import defusedxml.minidom

from simplify_redlines import (
    _can_merge_tracked,
    _find_elements,
    _get_author,
    get_tracked_change_authors,
    infer_author,
    simplify_redlines,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W_ATTR = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _parse(xml_str: str):
    return defusedxml.minidom.parseString(xml_str.encode("utf-8"))


def _make_doc(body_content: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document {W_ATTR}>'
        f"<w:body>{body_content}</w:body>"
        f"</w:document>"
    )


def _make_ins(author: str, content: str) -> str:
    return (
        f'<w:ins w:author="{author}" w:date="2024-01-01T00:00:00Z" w:id="1">'
        f"{content}"
        f"</w:ins>"
    )


def _make_del(author: str, content: str) -> str:
    return (
        f'<w:del w:author="{author}" w:date="2024-01-01T00:00:00Z" w:id="2">'
        f"{content}"
        f"</w:del>"
    )


def _write_doc(tmp_path: Path, body_content: str) -> Path:
    word_dir = tmp_path / "word"
    word_dir.mkdir(parents=True, exist_ok=True)
    doc = word_dir / "document.xml"
    doc.write_text(_make_doc(body_content), encoding="utf-8")
    return tmp_path


def _make_docx_zip(tmp_path: Path, body_content: str, name: str = "orig.docx") -> Path:
    docx_path = tmp_path / name
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr("word/document.xml", _make_doc(body_content))
    return docx_path


class TestGetAuthor:
    def test_reads_w_author_attribute(self):
        dom = _parse(
            f'<w:ins {W_ATTR} w:author="Alice" w:date="2024-01-01T00:00:00Z"/>'
        )
        elem = dom.documentElement
        assert _get_author(elem) == "Alice"

    def test_returns_empty_string_when_no_author(self):
        dom = _parse(f"<w:ins {W_ATTR}/>")
        assert _get_author(dom.documentElement) == ""


class TestCanMergeTracked:
    def _two_ins_doc(self, author1: str, author2: str, separator: str = ""):
        xml = _make_doc(
            f"<w:p>"
            f"{_make_ins(author1, '<w:r><w:t>a</w:t></w:r>')}"
            f"{separator}"
            f"{_make_ins(author2, '<w:r><w:t>b</w:t></w:r>')}"
            f"</w:p>"
        )
        dom = _parse(xml)
        ins_elems = _find_elements(dom.documentElement, "ins")
        return ins_elems

    def test_same_author_adjacent_can_merge(self):
        ins = self._two_ins_doc("Alice", "Alice")
        assert _can_merge_tracked(ins[0], ins[1])

    def test_different_authors_cannot_merge(self):
        ins = self._two_ins_doc("Alice", "Bob")
        assert not _can_merge_tracked(ins[0], ins[1])

    def test_element_node_between_prevents_merge(self):
        ins = self._two_ins_doc("Alice", "Alice", separator="<w:r/>")
        assert not _can_merge_tracked(ins[0], ins[1])

    def test_whitespace_text_node_between_allows_merge(self):
        ins = self._two_ins_doc("Alice", "Alice", separator="\n  ")
        assert _can_merge_tracked(ins[0], ins[1])


class TestSimplifyRedlinesIntegration:
    def test_adjacent_same_author_ins_merged(self, tmp_path):
        body = (
            "<w:p>"
            + _make_ins("Alice", "<w:r><w:t>Hello</w:t></w:r>")
            + _make_ins("Alice", "<w:r><w:t> World</w:t></w:r>")
            + "</w:p>"
        )
        _write_doc(tmp_path, body)
        count, _ = simplify_redlines(str(tmp_path))
        assert count == 1

        dom = defusedxml.minidom.parseString(
            (tmp_path / "word" / "document.xml").read_bytes()
        )
        ins_elems = _find_elements(dom.documentElement, "ins")
        assert len(ins_elems) == 1

    def test_different_author_ins_not_merged(self, tmp_path):
        body = (
            "<w:p>"
            + _make_ins("Alice", "<w:r><w:t>A</w:t></w:r>")
            + _make_ins("Bob", "<w:r><w:t>B</w:t></w:r>")
            + "</w:p>"
        )
        _write_doc(tmp_path, body)
        count, _ = simplify_redlines(str(tmp_path))
        assert count == 0

    def test_adjacent_same_author_del_merged(self, tmp_path):
        body = (
            "<w:p>"
            + _make_del("Alice", "<w:r><w:delText>x</w:delText></w:r>")
            + _make_del("Alice", "<w:r><w:delText>y</w:delText></w:r>")
            + "</w:p>"
        )
        _write_doc(tmp_path, body)
        count, _ = simplify_redlines(str(tmp_path))
        assert count == 1

    def test_ins_and_del_by_same_author_not_cross_merged(self, tmp_path):
        # ins and del must not merge with each other even if same author
        body = (
            "<w:p>"
            + _make_ins("Alice", "<w:r><w:t>add</w:t></w:r>")
            + _make_del("Alice", "<w:r><w:delText>remove</w:delText></w:r>")
            + "</w:p>"
        )
        _write_doc(tmp_path, body)
        count, _ = simplify_redlines(str(tmp_path))
        assert count == 0

    def test_missing_document_xml_returns_error(self, tmp_path):
        count, msg = simplify_redlines(str(tmp_path))
        assert count == 0
        assert "error" in msg.lower()

    def test_merged_ins_contains_all_children(self, tmp_path):
        body = (
            "<w:p>"
            + _make_ins("Alice", "<w:r><w:t>first</w:t></w:r>")
            + _make_ins("Alice", "<w:r><w:t>second</w:t></w:r>")
            + "</w:p>"
        )
        _write_doc(tmp_path, body)
        simplify_redlines(str(tmp_path))

        dom = defusedxml.minidom.parseString(
            (tmp_path / "word" / "document.xml").read_bytes()
        )
        runs = _find_elements(dom.documentElement, "r")
        assert len(runs) == 2


class TestGetTrackedChangeAuthors:
    def test_counts_insertions_by_author(self, tmp_path):
        body = (
            "<w:p>"
            + _make_ins("Alice", "<w:r><w:t>a</w:t></w:r>")
            + _make_ins("Alice", "<w:r><w:t>b</w:t></w:r>")
            + "</w:p>"
        )
        doc_xml = tmp_path / "document.xml"
        doc_xml.write_text(_make_doc(body), encoding="utf-8")
        authors = get_tracked_change_authors(doc_xml)
        assert authors["Alice"] == 2

    def test_counts_deletions_by_author(self, tmp_path):
        body = "<w:p>" + _make_del("Bob", "<w:r><w:delText>x</w:delText></w:r>") + "</w:p>"
        doc_xml = tmp_path / "document.xml"
        doc_xml.write_text(_make_doc(body), encoding="utf-8")
        authors = get_tracked_change_authors(doc_xml)
        assert authors["Bob"] == 1

    def test_multiple_authors_counted_separately(self, tmp_path):
        body = (
            "<w:p>"
            + _make_ins("Alice", "<w:r><w:t>a</w:t></w:r>")
            + _make_ins("Bob", "<w:r><w:t>b</w:t></w:r>")
            + "</w:p>"
        )
        doc_xml = tmp_path / "document.xml"
        doc_xml.write_text(_make_doc(body), encoding="utf-8")
        authors = get_tracked_change_authors(doc_xml)
        assert authors["Alice"] == 1
        assert authors["Bob"] == 1

    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert get_tracked_change_authors(tmp_path / "nope.xml") == {}


class TestInferAuthor:
    def test_single_new_author_identified(self, tmp_path):
        orig_body = "<w:p>" + _make_ins("Alice", "<w:r><w:t>a</w:t></w:r>") + "</w:p>"
        mod_body = (
            "<w:p>"
            + _make_ins("Alice", "<w:r><w:t>a</w:t></w:r>")
            + _make_ins("Bob", "<w:r><w:t>b</w:t></w:r>")
            + _make_ins("Bob", "<w:r><w:t>c</w:t></w:r>")
            + "</w:p>"
        )
        orig_docx = _make_docx_zip(tmp_path, orig_body)
        modified_dir = tmp_path / "modified"
        _write_doc(modified_dir, mod_body)

        author = infer_author(modified_dir, orig_docx)
        assert author == "Bob"

    def test_no_new_changes_returns_default(self, tmp_path):
        body = "<w:p>" + _make_ins("Alice", "<w:r><w:t>a</w:t></w:r>") + "</w:p>"
        orig_docx = _make_docx_zip(tmp_path, body)
        modified_dir = tmp_path / "modified"
        _write_doc(modified_dir, body)  # identical to original

        author = infer_author(modified_dir, orig_docx, default="Claude")
        assert author == "Claude"

    def test_multiple_new_authors_raises_value_error(self, tmp_path):
        orig_body = "<w:p/>"
        mod_body = (
            "<w:p>"
            + _make_ins("Alice", "<w:r><w:t>a</w:t></w:r>")
            + _make_ins("Bob", "<w:r><w:t>b</w:t></w:r>")
            + "</w:p>"
        )
        orig_docx = _make_docx_zip(tmp_path, orig_body)
        modified_dir = tmp_path / "modified"
        _write_doc(modified_dir, mod_body)

        with pytest.raises(ValueError, match="Multiple authors"):
            infer_author(modified_dir, orig_docx)
