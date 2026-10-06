import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from offspell.engine import Options, Speller  # noqa: E402

DATA = os.path.join(HERE, "data")
REAL = os.path.join(ROOT, "dictionaries")


@pytest.fixture
def speller(tmp_path):
    sp = Speller([DATA], personal_path=str(tmp_path / "personal.txt"), options=Options())
    sp.load()
    return sp


@pytest.fixture(scope="session")
def real_speller():
    """The real Mongolian + English dictionaries (skipped if not downloaded)."""
    if not os.path.isfile(os.path.join(REAL, "mn_MN.dic")):
        pytest.skip("run fetch_dictionaries.py to enable tests with the real dictionaries")
    sp = Speller([REAL], personal_path=None, options=Options())
    sp.load()
    return sp
