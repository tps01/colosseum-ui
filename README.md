# Colosseum UI

Optional Qt desktop runner and inspector for Colosseum. Distinct from the
`colosseum-gui` automation plugin (`col.gui.*`).

Docs: <https://tps01.github.io/colosseum-ui/>

Python 3.10+. Install a release wheel or, for development:

```sh
python -m pip install -r requirements.txt
```

Launch from an environment that already has `colosseum-core`:

```sh
colosseum --gui
# or
colosseum-ui
python -m colosseum_ui
```

Core alone returns an installation diagnostic for `--gui` until this package is
installed. Qt dependency pins stay in `pyproject.toml` (do not loosen casually).

## Offline bundles

Build a platform-specific offline archive (includes core + UI wheels):

```sh
python scripts/ci/build_offline_wheelhouse.py --also-build ../colosseum-core --archive
```

Release tags (`v*`) publish sdist/wheel and multi-platform offline houses via
GitHub Actions. Manual Windows bundles remain available from the Bundle workflow.

## Develop

```sh
python -m pytest
python -m ruff check colosseum_ui
python scripts/build_pages.py
```
