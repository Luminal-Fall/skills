"""Tests for init_skill.py — skill scaffolding logic."""

import stat
from pathlib import Path

import pytest
from init_skill import init_skill, title_case_skill_name


class TestTitleCaseSkillName:
    def test_single_word(self):
        assert title_case_skill_name("pdf") == "Pdf"

    def test_hyphenated_name(self):
        assert title_case_skill_name("my-cool-skill") == "My Cool Skill"

    def test_single_char(self):
        assert title_case_skill_name("a") == "A"

    def test_many_parts(self):
        assert title_case_skill_name("a-b-c-d") == "A B C D"

    def test_already_title_case_parts(self):
        assert title_case_skill_name("My-Skill") == "My Skill"

    def test_all_lowercase_parts_capitalized(self):
        assert title_case_skill_name("web-app-builder") == "Web App Builder"


class TestInitSkill:
    def test_creates_skill_directory(self, tmp_path):
        result = init_skill("my-skill", str(tmp_path))
        assert result is not None
        assert (tmp_path / "my-skill").is_dir()

    def test_returns_path_to_skill_dir(self, tmp_path):
        result = init_skill("test-skill", str(tmp_path))
        assert result == tmp_path / "test-skill"

    def test_creates_skill_md(self, tmp_path):
        init_skill("demo-skill", str(tmp_path))
        skill_md = tmp_path / "demo-skill" / "SKILL.md"
        assert skill_md.exists()

    def test_skill_md_contains_skill_name(self, tmp_path):
        init_skill("my-tool", str(tmp_path))
        content = (tmp_path / "my-tool" / "SKILL.md").read_text()
        assert "my-tool" in content

    def test_skill_md_contains_title_case_name(self, tmp_path):
        init_skill("my-tool", str(tmp_path))
        content = (tmp_path / "my-tool" / "SKILL.md").read_text()
        assert "My Tool" in content

    def test_creates_scripts_directory(self, tmp_path):
        init_skill("demo-skill", str(tmp_path))
        assert (tmp_path / "demo-skill" / "scripts").is_dir()

    def test_creates_references_directory(self, tmp_path):
        init_skill("demo-skill", str(tmp_path))
        assert (tmp_path / "demo-skill" / "references").is_dir()

    def test_creates_assets_directory(self, tmp_path):
        init_skill("demo-skill", str(tmp_path))
        assert (tmp_path / "demo-skill" / "assets").is_dir()

    def test_example_script_is_executable(self, tmp_path):
        init_skill("demo-skill", str(tmp_path))
        script = tmp_path / "demo-skill" / "scripts" / "example.py"
        assert script.exists()
        mode = script.stat().st_mode
        assert mode & stat.S_IXUSR, "example.py should have user-executable bit set"

    def test_example_script_contains_skill_name(self, tmp_path):
        init_skill("my-parser", str(tmp_path))
        content = (tmp_path / "my-parser" / "scripts" / "example.py").read_text()
        assert "my-parser" in content

    def test_existing_directory_returns_none(self, tmp_path):
        init_skill("existing", str(tmp_path))
        result = init_skill("existing", str(tmp_path))
        assert result is None

    def test_existing_directory_does_not_overwrite_skill_md(self, tmp_path):
        init_skill("guarded", str(tmp_path))
        original = (tmp_path / "guarded" / "SKILL.md").read_text()
        (tmp_path / "guarded" / "SKILL.md").write_text("custom content")
        init_skill("guarded", str(tmp_path))
        assert (tmp_path / "guarded" / "SKILL.md").read_text() == "custom content"

    def test_relative_path_resolves_correctly(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = init_skill("resolved-skill", ".")
        assert result is not None
        assert result.is_absolute()
        assert (result / "SKILL.md").exists()

    def test_reference_doc_created(self, tmp_path):
        init_skill("ref-skill", str(tmp_path))
        ref = tmp_path / "ref-skill" / "references" / "api_reference.md"
        assert ref.exists()

    def test_asset_placeholder_created(self, tmp_path):
        init_skill("asset-skill", str(tmp_path))
        asset = tmp_path / "asset-skill" / "assets" / "example_asset.txt"
        assert asset.exists()
