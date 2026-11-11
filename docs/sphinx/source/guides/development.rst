Development
===========

Clone the repository next to ``colosseum-core`` when iterating on both packages.

::

   python -m venv .venv
   python -m pip install -r requirements.txt
   python -m pytest
   python -m ruff check colosseum_ui

On Linux CI and headless hosts, set ``QT_QPA_PLATFORM=offscreen`` and install
system libraries such as ``libegl1`` / ``libgl1`` when Qt needs them.

Build this documentation site locally (requires pandoc and Sphinx)::

   python -m pip install "sphinx>=7.0,<9"
   python scripts/build_pages.py

GitHub Actions publishes Pages from ``develop`` / ``main`` via the Documentation
workflow. Tag ``vX.Y.Z`` on ``main`` (matching ``pyproject.toml``) to publish
wheels and offline archives.
