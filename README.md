# Colosseum UI

Optional desktop inspector, distinct from the colosseum-gui automation plugin.
Python 3.10+. Install: `python -m pip install -r requirements.txt`.
Launch from your workspace: `python -m colosseum_ui` or `colosseum-ui`.

Gate 1: read-only history, logs, summaries and suite navigation. Gate 2 adds execution inputs, live output, asynchronous Stop and close handling. Polish follows in gate 3, core cutover and offline bundles in gate 4. Core GUI remains available until cutover.

Qt dependencies remain unmodified. Run `python -m pytest` and `python -m ruff check .`.

Gate 3 adds System/Light/Dark appearance, accessible compact pickers, log wrapping, paged raw logs (all text retained in temporary storage), and batched history population. Previous/Next page navigate large logs. Appearance remains session-only.

Desktop GUI: install the separate `colosseum-ui` wheel (Python 3.10+), then run `colosseum --gui`. Core alone returns an installation diagnostic. Qt dependencies are unmodified.

Build a platform-specific offline bundle from the UI repo:

```
python scripts/ci/build_offline_wheelhouse.py --also-build ../colosseum-core --archive
```

Use a fresh wheelhouse directory. Bundles contain the local core/UI wheels and
unmodified third-party wheels with vendor notices. Run install.bat (Windows) or
install.sh (Linux), then start_gui.bat/start_gui.sh. Core-only bundles expose CLI
launchers only. Frozen core executables deliberately exclude colosseum_ui.

The initial local migration wheel is a development artifact; publish a coordinated
core/UI release before directing existing users to upgrade through release channels.
