Getting started
===============

``colosseum-ui`` is the optional Qt desktop runner for Colosseum. It is distinct
from the ``colosseum-gui`` automation plugin (``col.gui.*``).

Requirements
------------

* Python 3.10 or newer
* ``colosseum-core`` in the same virtual environment
* A display (or ``QT_QPA_PLATFORM=offscreen`` for headless smoke only)

Install
-------

From a GitHub Release wheel::

   python -m pip install "./colosseum_ui-<version>-py3-none-any.whl"

Or for development, from a clone::

   python -m pip install -r requirements.txt

Launch
------

Any of these work after install::

   colosseum --gui
   colosseum-ui
   python -m colosseum_ui

Core alone prints an installation diagnostic when ``--gui`` is used without
``colosseum-ui``.

Offline bundles
---------------

Release assets include offline wheelhouses that package ``colosseum-ui``,
``colosseum-core``, and third-party wheels (including Qt). Extract the archive
for your OS/Python, run ``install.bat`` / ``install.sh``, then
``start_gui.bat`` / ``start_gui.sh``.

See the `GitHub repository <https://github.com/tps01/colosseum-ui>`__ and
`core hub <https://tps01.github.io/colosseum-core/>`__.
