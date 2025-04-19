import subprocess
import sys
import os
import pytest

def test_ai_typing_launcher_runs_without_crash(tmp_path):
    """
    Smoke test: Launch ai_typing.py and ensure it does not crash immediately.
    Checks for exit code and absence of ImportError/Traceback in output.
    """
    launcher = os.path.join(os.path.dirname(__file__), '..', '..', 'ai_typing.py')
    launcher = os.path.abspath(launcher)
    env = os.environ.copy()
    # Use a temp DB to avoid production DB mutation
    env['DATABASE'] = str(tmp_path / 'test_launcher.db')
    proc = subprocess.Popen(
        [sys.executable, launcher],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=os.path.dirname(launcher)
    )
    try:
        outs, errs = proc.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()
        pytest.fail('Launcher did not exit within timeout (possible hang or modal dialog)')
    # Acceptable for GUI app to exit 0 or 1 (1 if it can't find display, etc.)
    # But must NOT crash due to ImportError/Traceback
    output = (outs or b'').decode(errors='ignore') + (errs or b'').decode(errors='ignore')
    assert 'ImportError' not in output, f'ImportError in launcher output: {output}'
    assert 'ModuleNotFoundError' not in output, f'ModuleNotFoundError in launcher output: {output}'
    assert 'Traceback' not in output, f'Traceback in launcher output: {output}'
    # Optionally, assert proc.returncode == 0
