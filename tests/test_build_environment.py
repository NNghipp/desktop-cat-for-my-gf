import os
from pathlib import Path

from tools.build_exe import build_environment


def test_build_does_not_search_unrelated_dll_directories(monkeypatch):
    monkeypatch.setenv("PATH", "C:/unrelated/poppler;C:/unrelated/conda")
    monkeypatch.setenv("PYTHONPATH", "C:/unrelated/modules")
    monkeypatch.setenv("QT_PLUGIN_PATH", "C:/unrelated/Qt/plugins")
    env = build_environment()
    assert "unrelated" not in env["PATH"]
    assert str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32").lower() in env["PATH"].lower()
    assert "PYTHONPATH" not in env
    assert "QT_PLUGIN_PATH" not in env
    assert "unrelated" in os.environ["PATH"]  # The user's environment is untouched.
