"""Build and test a self-contained Windows EXE in a controlled DLL environment."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def build_environment() -> dict[str, str]:
    env = os.environ.copy()
    windows = Path(os.environ.get("SystemRoot", "C:/Windows"))
    # A host PATH may contain Poppler/Conda's icuuc.dll (with versioned exports).
    # Qt 6.12 uses the Windows ICU DLL (unversioned exports). Letting PyInstaller
    # inspect those unrelated directories silently produces a broken bundle.
    env["PATH"] = os.pathsep.join(map(str, [Path(sys.executable).parent,
                                          Path(sys.base_prefix),
                                          windows / "System32", windows]))
    for key in ("PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QML2_IMPORT_PATH"):
        env.pop(key, None)
    return env


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Build on Windows to create DesktopCat.exe.")
    env = build_environment()
    subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, env=env, check=True)
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "tools/desktop_cat.spec",
    ], cwd=ROOT, env=env, check=True)
    exe = ROOT / "dist" / "DesktopCat.exe"
    # Only the EXE is copied. No source tree, venv or images can mask missing files.
    with tempfile.TemporaryDirectory(prefix="DesktopCat-smoke-") as directory:
        portable = Path(directory) / exe.name
        shutil.copy2(exe, portable)
        smoke_env = env.copy()
        for key in ("QT_QPA_PLATFORM", "QT_SCALE_FACTOR", "QT_SCREEN_SCALE_FACTORS"):
            smoke_env.pop(key, None)
        subprocess.run([str(portable), "--smoke-test"], cwd=directory,
                       env=smoke_env, timeout=30, check=True)
    print(f"Portable EXE smoke test passed: {exe}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
