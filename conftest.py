"""Put the repository root on ``sys.path`` before any test is collected.

``core`` and ``interfaces`` are namespace packages: they have no
``__init__.py``, so they resolve against ``sys.path`` rather than against the
importing file's own folder. Nothing puts the repository root there
automatically.

``pytest`` reads the ``pythonpath`` setting in ``pyproject.toml``, which covers
the plain ``pytest`` and ``python -m pytest`` cases. It does not cover every
runner: an IDE that imports a test module directly, or a tool that collects with
a different rootdir, still fails with ``No module named 'interfaces'``. pytest
loads the rootdir ``conftest.py`` before it imports anything else, so doing the
insert here works in all of them.

Delete this file once the project is installed as a real package
(``pip install -e .``), which puts the modules on the path properly and makes
the whole question go away.
"""
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
