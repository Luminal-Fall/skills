"""Tests for clean.py — PPTX orphaned file removal logic."""

import textwrap
from pathlib import Path

import pytest

defusedxml = pytest.importorskip("defusedxml", reason="defusedxml not installed")

from clean import (
    clean_unused_files,
    get_slides_in_sldidlst,
    remove_orphaned_slides,
    remove_trash_directory,
    update_content_types,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip(), encoding="utf-8")


def _make_pptx_dirs(base: Path) -> None:
    for d in ["ppt/slides/_rels", "ppt/_rels", "ppt/media", "ppt/theme"]:
        (base / d).mkdir(parents=True, exist_ok=True)


def _make_presentation_xml(base: Path, slide_rids: list[str]) -> None:
    slides_xml = "".join(
        f'<p:sldId id="{200 + i}" r:id="{rid}"/>'
        for i, rid in enumerate(slide_rids)
    )
    _write(
        base / "ppt" / "presentation.xml",
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        f'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<p:sldIdLst>{slides_xml}</p:sldIdLst>"
        f"</p:presentation>",
    )


def _make_rels(base: Path, rels_path: str, relationships: list[dict]) -> None:
    rel_entries = "".join(
        f'<Relationship Id="{r["id"]}" Type="{r["type"]}" Target="{r["target"]}"/>'
        for r in relationships
    )
    _write(
        base / rels_path,
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{rel_entries}"
        f"</Relationships>",
    )


def _make_content_types(base: Path, overrides: list[tuple[str, str]]) -> None:
    override_xml = "".join(
        f'<Override PartName="{part}" ContentType="{ct}"/>'
        for part, ct in overrides
    )
    _write(
        base / "[Content_Types].xml",
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        f"{override_xml}"
        f"</Types>",
    )


class TestGetSlidesInSldIdLst:
    def test_returns_referenced_slide_names(self, tmp_path):
        _make_pptx_dirs(tmp_path)
        _make_presentation_xml(tmp_path, ["rId1"])
        _make_rels(
            tmp_path,
            "ppt/_rels/presentation.xml.rels",
            [{"id": "rId1", "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide", "target": "slides/slide1.xml"}],
        )
        result = get_slides_in_sldidlst(tmp_path)
        assert "slide1.xml" in result

    def test_excludes_unreferenced_slides(self, tmp_path):
        _make_pptx_dirs(tmp_path)
        _make_presentation_xml(tmp_path, ["rId1"])
        _make_rels(
            tmp_path,
            "ppt/_rels/presentation.xml.rels",
            [
                {"id": "rId1", "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide", "target": "slides/slide1.xml"},
                {"id": "rId2", "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide", "target": "slides/slide2.xml"},
            ],
        )
        result = get_slides_in_sldidlst(tmp_path)
        assert "slide1.xml" in result
        assert "slide2.xml" not in result

    def test_returns_empty_set_when_files_missing(self, tmp_path):
        result = get_slides_in_sldidlst(tmp_path)
        assert result == set()


class TestRemoveOrphanedSlides:
    def _setup_two_slides(self, tmp_path: Path, rels: list[str]) -> None:
        _make_pptx_dirs(tmp_path)
        _make_presentation_xml(tmp_path, rels)
        _make_rels(
            tmp_path,
            "ppt/_rels/presentation.xml.rels",
            [
                {"id": "rId1", "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide", "target": "slides/slide1.xml"},
                {"id": "rId2", "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide", "target": "slides/slide2.xml"},
            ],
        )
        _write(tmp_path / "ppt" / "slides" / "slide1.xml", "<slide/>")
        _write(tmp_path / "ppt" / "slides" / "slide2.xml", "<slide/>")

    def test_orphaned_slide_is_deleted(self, tmp_path):
        self._setup_two_slides(tmp_path, ["rId1"])  # only slide1 referenced
        remove_orphaned_slides(tmp_path)
        assert not (tmp_path / "ppt" / "slides" / "slide2.xml").exists()

    def test_referenced_slide_is_kept(self, tmp_path):
        self._setup_two_slides(tmp_path, ["rId1"])
        remove_orphaned_slides(tmp_path)
        assert (tmp_path / "ppt" / "slides" / "slide1.xml").exists()

    def test_returns_list_of_removed_paths(self, tmp_path):
        self._setup_two_slides(tmp_path, ["rId1"])
        removed = remove_orphaned_slides(tmp_path)
        assert any("slide2.xml" in r for r in removed)

    def test_no_orphans_returns_empty_list(self, tmp_path):
        self._setup_two_slides(tmp_path, ["rId1", "rId2"])
        removed = remove_orphaned_slides(tmp_path)
        assert removed == []

    def test_missing_slides_dir_returns_empty_list(self, tmp_path):
        assert remove_orphaned_slides(tmp_path) == []


class TestRemoveTrashDirectory:
    def test_removes_trash_directory_and_contents(self, tmp_path):
        trash = tmp_path / "[trash]"
        trash.mkdir()
        (trash / "old_slide.xml").write_text("<slide/>")
        remove_trash_directory(tmp_path)
        assert not trash.exists()

    def test_returns_list_of_removed_files(self, tmp_path):
        trash = tmp_path / "[trash]"
        trash.mkdir()
        (trash / "junk.xml").write_text("<junk/>")
        removed = remove_trash_directory(tmp_path)
        assert len(removed) == 1
        assert "junk.xml" in removed[0]

    def test_no_trash_dir_returns_empty_list(self, tmp_path):
        assert remove_trash_directory(tmp_path) == []


class TestUpdateContentTypes:
    def test_removes_override_for_deleted_file(self, tmp_path):
        _make_content_types(
            tmp_path,
            [
                ("/ppt/slides/slide1.xml", "application/vnd.ct.slide"),
                ("/ppt/slides/slide2.xml", "application/vnd.ct.slide"),
            ],
        )
        update_content_types(tmp_path, ["ppt/slides/slide2.xml"])

        import defusedxml.minidom
        dom = defusedxml.minidom.parse(str(tmp_path / "[Content_Types].xml"))
        overrides = dom.getElementsByTagName("Override")
        part_names = [o.getAttribute("PartName") for o in overrides]
        assert "/ppt/slides/slide1.xml" in part_names
        assert "/ppt/slides/slide2.xml" not in part_names

    def test_strips_leading_slash_from_part_name(self, tmp_path):
        # PartName="/ppt/media/image1.png" in XML must match "ppt/media/image1.png"
        _make_content_types(tmp_path, [("/ppt/media/image1.png", "image/png")])
        update_content_types(tmp_path, ["ppt/media/image1.png"])

        import defusedxml.minidom
        dom = defusedxml.minidom.parse(str(tmp_path / "[Content_Types].xml"))
        overrides = dom.getElementsByTagName("Override")
        assert len(overrides) == 0

    def test_no_op_when_content_types_absent(self, tmp_path):
        # Should not crash when [Content_Types].xml doesn't exist
        update_content_types(tmp_path, ["ppt/slides/slide1.xml"])

    def test_unrelated_overrides_preserved(self, tmp_path):
        _make_content_types(
            tmp_path,
            [
                ("/ppt/slides/slide1.xml", "application/vnd.ct.slide"),
                ("/docProps/core.xml", "application/vnd.ct.core"),
            ],
        )
        update_content_types(tmp_path, ["ppt/slides/slide1.xml"])

        import defusedxml.minidom
        dom = defusedxml.minidom.parse(str(tmp_path / "[Content_Types].xml"))
        overrides = dom.getElementsByTagName("Override")
        part_names = [o.getAttribute("PartName") for o in overrides]
        assert "/docProps/core.xml" in part_names


class TestCleanUnusedFilesIntegration:
    def test_orphaned_media_file_removed(self, tmp_path):
        _make_pptx_dirs(tmp_path)
        _make_presentation_xml(tmp_path, [])
        _make_rels(tmp_path, "ppt/_rels/presentation.xml.rels", [])

        # Create an unreferenced media file
        media = tmp_path / "ppt" / "media" / "image1.png"
        media.write_bytes(b"fake_png_data")

        _make_content_types(tmp_path, [("/ppt/media/image1.png", "image/png")])
        removed = clean_unused_files(tmp_path)
        assert not media.exists()

    def test_empty_pptx_structure_no_crash(self, tmp_path):
        _make_pptx_dirs(tmp_path)
        _make_presentation_xml(tmp_path, [])
        _make_rels(tmp_path, "ppt/_rels/presentation.xml.rels", [])
        _make_content_types(tmp_path, [])
        removed = clean_unused_files(tmp_path)
        assert isinstance(removed, list)
