"""Tests for scripts/check_frontend.py frontend hygiene guards."""

from pathlib import Path

from scripts.check_frontend import (
    BASE_DIR,
    check_case_collisions,
    check_css_files,
    check_django_templates,
)


def test_repo_has_no_case_insensitive_collisions():
    errors = check_case_collisions([BASE_DIR / "templates", BASE_DIR / "static"])
    assert errors == []


def test_repo_css_passes_balance_and_no_import_guard():
    errors = check_css_files(BASE_DIR / "static")
    assert errors == []


def test_repo_all_django_templates_compile_cleanly():
    errors = check_django_templates(BASE_DIR / "templates")
    assert errors == []


def test_case_collision_detector_catches_duplicates(tmp_path: Path):
    (tmp_path / "Desarrollador").mkdir()
    (tmp_path / "desarrollador").mkdir()
    errors = check_case_collisions([tmp_path])
    assert len(errors) == 1
    assert "collision" in errors[0].lower()


def test_css_guard_catches_unbalanced_braces_and_import(tmp_path: Path):
    bad_import = tmp_path / "a.css"
    bad_import.write_text('@import url("other.css");\nbody { color: red; }\n', encoding="utf-8")

    bad_brace = tmp_path / "b.css"
    bad_brace.write_text("body { color: red;\n", encoding="utf-8")

    valid_with_svg = tmp_path / "c.css"
    valid_with_svg.write_text(
        '/* @import ignored in comment */\nbody { background: url("data:image/svg+xml,{"); }\n',
        encoding="utf-8",
    )

    errors = check_css_files(tmp_path)
    assert any("a.css" in err and "@import" in err for err in errors)
    assert any("b.css" in err and "Unclosed" in err for err in errors)
    assert not any("c.css" in err for err in errors)
