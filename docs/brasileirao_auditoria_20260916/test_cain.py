import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent / "cain"
os.chdir(root)
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
(root / 'temp').mkdir(exist_ok=True)
os.environ['TMP'] = os.environ['TEMP'] = str(root / 'temp')
import tempfile
tempfile.tempdir = str(root / 'temp')
sys.dont_write_bytecode = True
sys.path[:0] = [str(root / 'src'), str(root / 'tests/integration'),
    'C:/CAIN/work/conversation-v2-20260914/installed-qa-matched/Lib/site-packages']
sys.path.append('C:/BRASILEIRAO/work/im26/.venv/Lib/site-packages')
import pytest


def audit(event, args):
    if event.startswith('socket.') and event != 'socket.gethostname':
        raise RuntimeError('Network disabled in QA')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1:3]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if writing and not path.is_relative_to(root):
            raise RuntimeError(f'Write outside QA: {path}')
        if path.is_relative_to(Path('C:/CAIN/projeto')):
            raise RuntimeError('Primary CAIN read forbidden during tests')


sys.addaudithook(audit)
raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', '--log-file', str(root / 'pytest.log'),
    '--basetemp', str(root / 'tmp'), 'tests/integration/test_br_audit_instructions.py',
    'tests/integration/test_grounded_analysis.py', 'tests/integration/test_literal_claim_tables.py', 'tests/test_hypothesis_catalog.py']))
