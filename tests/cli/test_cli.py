import subprocess
import sys


def test_unwritable_database_reports_error_without_traceback(tmp_path):
    invalid_db = tmp_path / "directory-is-not-a-database"
    invalid_db.mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "cain", "run", "Resuma este texto", "--db", str(invalid_db)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 1
    assert "Cain:" in result.stderr
    assert "Traceback" not in result.stderr
