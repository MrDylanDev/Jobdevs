#!/usr/bin/env python3
"""Lightweight frontend hygiene checks for JobDevs.

Validates:
1. No case-insensitive path collisions in templates/ or static/.
2. CSS brace balance and zero @import rules in non-vendor static/**/*.css.
3. Django template syntax compilation across templates/**/*.html.
4. JS syntax via `node --check` on non-vendor static/**/*.js (when Node is available
   or required via --require-node in CI).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IGNORED_DIR_NAMES = {"vendor", "__pycache__", ".git", "node_modules"}
CSS_COMMENT_OR_STRING_RE = re.compile(
    r"/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
    re.DOTALL,
)
CSS_IMPORT_RE = re.compile(r"@import\b", re.IGNORECASE)


def _is_ignored(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    return any(part in IGNORED_DIR_NAMES for part in rel_parts)


def check_case_collisions(roots: list[Path]) -> list[str]:
    """Return errors for any case-insensitive file/dir collisions under each root."""
    errors: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        seen: dict[str, Path] = {}
        for path in sorted(root.rglob("*")):
            if _is_ignored(path, root):
                continue
            rel_posix = path.relative_to(root).as_posix()
            key = rel_posix.lower()
            if key in seen:
                errors.append(
                    f"Case-insensitive collision under {root.name}/: "
                    f"{seen[key].relative_to(root).as_posix()} vs {rel_posix}"
                )
            else:
                seen[key] = path
    return errors


def _strip_css_comments_and_strings(css_text: str) -> str:
    return CSS_COMMENT_OR_STRING_RE.sub("", css_text)


def check_css_files(static_dir: Path) -> list[str]:
    """Return errors for unbalanced braces or @import rules in non-vendor CSS."""
    errors: list[str] = []
    if not static_dir.exists():
        return errors

    for css_file in sorted(static_dir.rglob("*.css")):
        if _is_ignored(css_file, static_dir):
            continue
        raw = css_file.read_text(encoding="utf-8")
        cleaned = _strip_css_comments_and_strings(raw)
        rel = css_file.relative_to(static_dir).as_posix()

        if CSS_IMPORT_RE.search(cleaned):
            errors.append(f"Disallowed @import in static/{rel}")

        depth = 0
        for ch in cleaned:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    errors.append(f"Unmatched closing '}}' in static/{rel}")
                    break
        if depth > 0:
            errors.append(f"Unclosed '{{' (depth={depth}) in static/{rel}")

    return errors


def check_django_templates(templates_dir: Path) -> list[str]:
    """Compile every HTML template under templates_dir using Django's template engine."""
    errors: list[str] = []
    if not templates_dir.exists():
        return errors

    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("DJANGO_SECRET_KEY", "frontend-check-dummy-key")
    os.environ.setdefault("DJANGO_DEBUG", "True")

    import django
    from django.apps import apps
    from django.template import TemplateSyntaxError
    from django.template.loader import get_template

    if not apps.ready:
        django.setup()

    for tpl_file in sorted(templates_dir.rglob("*.html")):
        if _is_ignored(tpl_file, templates_dir):
            continue
        rel = tpl_file.relative_to(templates_dir).as_posix()
        try:
            get_template(rel)
        except TemplateSyntaxError as exc:
            errors.append(f"TemplateSyntaxError in templates/{rel}: {exc}")

    return errors


def check_js_files(static_dir: Path, *, require_node: bool = False) -> tuple[list[str], bool]:
    """Validate JS syntax using `node --check`. Returns (errors, ran_node)."""
    node_bin = shutil.which("node")
    if not node_bin:
        if require_node:
            return ["Node.js binary 'node' is required (--require-node) but not found in PATH."], False
        return [], False

    errors: list[str] = []
    if not static_dir.exists():
        return errors, True

    for js_file in sorted(static_dir.rglob("*.js")):
        if _is_ignored(js_file, static_dir):
            continue
        rel = js_file.relative_to(static_dir).as_posix()
        res = subprocess.run(
            [node_bin, "--check", str(js_file)],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            stderr = (res.stderr or "").strip()
            # Fallback for ES modules when Node defaults .js to CommonJS.
            if (
                "Cannot use import statement outside a module" in stderr
                or "Unexpected token 'export'" in stderr
                or "import.meta" in stderr
            ):
                source = js_file.read_text(encoding="utf-8")
                esm_res = subprocess.run(
                    [node_bin, "--input-type=module", "--check"],
                    input=source,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if esm_res.returncode == 0:
                    continue
                stderr = (esm_res.stderr or stderr).strip()
            first_line = stderr.splitlines()[0] if stderr else "syntax error"
            errors.append(f"JS syntax error in static/{rel}: {first_line}")

    return errors, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run JobDevs frontend hygiene checks.")
    parser.add_argument(
        "--require-node",
        action="store_true",
        help="Fail if `node` is not available in PATH.",
    )
    args = parser.parse_args(argv)

    templates_dir = BASE_DIR / "templates"
    static_dir = BASE_DIR / "static"

    errors: list[str] = []
    errors.extend(check_case_collisions([templates_dir, static_dir]))
    errors.extend(check_css_files(static_dir))
    errors.extend(check_django_templates(templates_dir))
    js_errors, ran_node = check_js_files(static_dir, require_node=args.require_node)
    errors.extend(js_errors)

    if not ran_node and not args.require_node:
        print("WARN: 'node' not found in PATH; skipped JS syntax check (use --require-node in CI).")

    if errors:
        print(f"Frontend checks FAILED ({len(errors)} issue(s)):")
        for err in errors:
            print(f"  - {err}")
        return 1

    node_status = "including JS syntax (node --check)" if ran_node else "templates + CSS + case-collisions"
    print(f"Frontend checks passed ({node_status}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
