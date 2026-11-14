#!/usr/bin/env python3
"""Build GitHub Pages HTML for Colosseum UI."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

# --- package constants ---
TITLE = "Colosseum Extensions"
SLUG = "extensions"
# (rst_stem, import_module, displayed name)
API_MODULES: tuple[tuple[str, str, str], ...] = (
    ("app", "colosseum_extensions.ui.app", "colosseum_extensions.ui.app"),
    ("artifacts", "colosseum_extensions.ui.artifacts", "colosseum_extensions.ui.artifacts"),
    ("console", "colosseum_extensions.ui.console", "colosseum_extensions.ui.console"),
    ("execution", "colosseum_extensions.ui.execution", "colosseum_extensions.ui.execution"),
    ("theme", "colosseum_extensions.ui.theme", "colosseum_extensions.ui.theme"),
)
GUIDES: tuple[str, ...] = (
    "docs/sphinx/source/guides/getting_started.rst",
    "docs/sphinx/source/guides/development.rst",
)
# --- end constants ---

HUB_URL = "https://tps01.github.io/colosseum-core/"
REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = REPO_ROOT / "build" / "pages"
SITE_SOURCE = BUILD_ROOT / "source"
HTML_DIR = BUILD_ROOT / "html"

_MOCK_IMPORTS = (
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
)


def _read_version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _pandoc_readme(dest: Path) -> None:
    readme = REPO_ROOT / "README.md"
    if not readme.is_file():
        raise SystemExit(f"Missing README: {readme}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pandoc", str(readme), "-f", "markdown", "-t", "rst", "-o", str(dest)],
        check=True,
    )


def _write_conf(version: str) -> None:
    pages_url = f"https://tps01.github.io/colosseum-{SLUG}/"
    mocks = ", ".join(f'"{name}"' for name in _MOCK_IMPORTS)
    conf = f'''"""Sphinx configuration for {TITLE} GitHub Pages."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

project = "{TITLE}"
copyright = "tps01"
author = "tps01"
release = "{version}"

master_doc = "index"
root_doc = "index"

extensions = ["sphinx.ext.autodoc"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = ["_static"]
html_logo = "_static/colosseum-logo.png"
html_favicon = "_static/colosseum.ico"
html_theme_options = {{
    "logo_name": True,
}}
html_baseurl = "{pages_url}"

autodoc_member_order = "bysource"
autodoc_typehints = "signature"
autodoc_default_options = {{
    "members": True,
    "undoc-members": False,
    "show-inheritance": False,
}}
autodoc_mock_imports = [{mocks}]
'''
    (SITE_SOURCE / "conf.py").write_text(conf, encoding="utf-8")


def _write_module_page(stem: str, module: str, display: str) -> str:
    api_dir = SITE_SOURCE / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    title = display
    body = f"""{title}
{"=" * len(title)}

.. automodule:: {module}
   :members:
"""
    (api_dir / f"{stem}.rst").write_text(body, encoding="utf-8")
    return f"api/{stem}"


def _copy_branding() -> None:
    static = SITE_SOURCE / "_static"
    static.mkdir(parents=True, exist_ok=True)
    candidates = (
        REPO_ROOT / ".deps" / "colosseum-core" / "docs" / "sphinx" / "source" / "_static",
        REPO_ROOT.parent / "colosseum-core" / "docs" / "sphinx" / "source" / "_static",
        REPO_ROOT / "colosseum_extensions" / "ui" / "assets",
    )
    for core_static in candidates:
        if not core_static.is_dir():
            continue
        for name, dest_name in (
            ("colosseum-logo.png", "colosseum-logo.png"),
            ("colosseum.ico", "colosseum.ico"),
            ("colosseum-512.png", "colosseum-logo.png"),
        ):
            src = core_static / name
            dest = static / dest_name
            if src.is_file() and not dest.is_file():
                shutil.copy2(src, dest)


def _write_index(api_docs: list[str], guide_names: list[str]) -> None:
    lines = [
        TITLE,
        "=" * len(TITLE),
        "",
        "Optional Colosseum extensions, including a Qt desktop runner and inspector.",
        "Install beside ``colosseum-core``, then launch with ``colosseum --gui``.",
        "",
        f"`Colosseum core documentation hub <{HUB_URL}>`__",
        "",
    ]
    development = [name for name in guide_names if name.endswith("/development")]
    learning = [name for name in guide_names if name not in development]
    sections = (
        ("Overview", ["readme"]),
        ("Guides", learning),
        ("API reference", api_docs),
        ("Development", development),
    )
    for caption, names in sections:
        if names:
            lines.extend(
                [
                    ".. toctree::",
                    "   :maxdepth: 1",
                    "   :titlesonly:",
                    f"   :caption: {caption}",
                    "",
                ]
            )
            lines.extend(f"   {name}" for name in names)
            lines.append("")
    (SITE_SOURCE / "index.rst").write_text("\n".join(lines), encoding="utf-8")
    _copy_branding()


def stage() -> None:
    if SITE_SOURCE.exists():
        shutil.rmtree(SITE_SOURCE)
    SITE_SOURCE.mkdir(parents=True)

    _pandoc_readme(SITE_SOURCE / "readme.rst")

    api_docs: list[str] = []
    for stem, module, display in API_MODULES:
        api_docs.append(_write_module_page(stem, module, display))

    guide_names: list[str] = []
    guides_dir = SITE_SOURCE / "guides"
    for rel in GUIDES:
        src = REPO_ROOT / rel
        if not src.is_file():
            raise SystemExit(f"Missing guide: {src}")
        guides_dir.mkdir(parents=True, exist_ok=True)
        name = Path(rel).stem
        guide_names.append(f"guides/{name}")
        (guides_dir / f"{name}.rst").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    _write_conf(_read_version())
    _write_index(api_docs, guide_names)


def build_html() -> Path:
    stage()
    if HTML_DIR.exists():
        shutil.rmtree(HTML_DIR)
    HTML_DIR.mkdir(parents=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            "-W",
            "--keep-going",
            str(SITE_SOURCE),
            str(HTML_DIR),
        ],
        check=True,
    )
    (HTML_DIR / "version.txt").write_text(_read_version() + "\n", encoding="utf-8")
    return HTML_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Build {TITLE} GitHub Pages HTML")
    parser.add_argument(
        "--stage-only",
        action="store_true",
        help="Stage Sphinx sources without building HTML",
    )
    args = parser.parse_args(argv)
    if args.stage_only:
        stage()
        print(SITE_SOURCE)
        return 0
    out = build_html()
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
