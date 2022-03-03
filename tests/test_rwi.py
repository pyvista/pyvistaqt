import sys
from mne.utils import run_subprocess


def test_rwi(qapp):
    stdout, stderr, code = run_subprocess([sys.executable, 'pyvistaqt/rwi.py'],
                                          return_code=True)
    assert code == 0, stdout + stderr
