Getting started
===============

``colosseum-extensions`` provides optional Colosseum extensions. Its
``colosseum_extensions.ui`` subpackage is the Qt desktop runner, distinct from
the ``colosseum-gui`` automation plugin (``col.gui.*``).

Requirements
------------

* Python 3.10 or newer
* ``colosseum-core`` 0.18.11 or newer in the 0.18 series, in the same virtual environment
* A display (or ``QT_QPA_PLATFORM=offscreen`` for headless smoke only)

Install
-------

From a GitHub Release wheel::

   python -m pip install "./colosseum_extensions-<version>-py3-none-any.whl"

Or for development, from a clone::

   python -m pip install -r requirements.txt

Launch
------

Any of these work after install::

   colosseum --gui
   colosseum-extensions
   python -m colosseum_extensions.ui

Core alone prints an installation diagnostic when ``--gui`` is used without
``colosseum-extensions``.

The UI remembers selected files, appearance, window layout, and working directory
in per-user settings. The working directory controls relative paths and output
history. Nonempty bench config and metadata environment variables take precedence
over saved selections. No run starts automatically on reopening.

Offline bundles
---------------

Release assets include offline wheelhouses that package ``colosseum-extensions``,
``colosseum-core``, and third-party wheels (including Qt). Extract the archive
for your OS/Python, run ``install.bat`` / ``install.sh``, then
``start_gui.bat`` / ``start_gui.sh``.

See the `GitHub repository <https://github.com/tps01/colosseum-extensions>`__ and
`core hub <https://tps01.github.io/colosseum-core/>`__.
