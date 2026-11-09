from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "desktop_cat/assets"), "desktop_cat/assets")],
    hiddenimports=[],
    excludes=["PySide6.QtNetwork"],
)
# This application paints PNGs using QWidget's raster backend on Windows.
qt_libraries = {
    "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll",
    "QtCore.pyd", "QtGui.pyd", "QtWidgets.pyd", "pyside6.abi3.dll",
    "MSVCP140.dll", "MSVCP140_1.dll", "MSVCP140_2.dll",
    "VCRUNTIME140.dll", "VCRUNTIME140_1.dll",
}
qt_plugins = {
    "PySide6/plugins/platforms/qwindows.dll",
    "PySide6/plugins/styles/qmodernwindowsstyle.dll",
    "PySide6/plugins/imageformats/qico.dll",
}
def needed(entry):
    name = entry[0].replace("\\", "/")
    if not name.startswith("PySide6/"):
        return True
    return name in qt_plugins or name.split("/")[-1] in qt_libraries

a.binaries = [entry for entry in a.binaries if needed(entry)]
a.datas = [entry for entry in a.datas
           if not entry[0].replace("\\", "/").startswith("PySide6/translations/")]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="DesktopCat", debug=False, strip=False, upx=False,
    console=False, icon=str(root / "desktop_cat/assets/cat.ico"),
)
