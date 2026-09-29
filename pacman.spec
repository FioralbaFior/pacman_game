# PyInstaller specification, kept at the repository root as required.
#
# The assigned A-Maze-ing package is collected explicitly so the frozen
# build does not depend on the reviewer's site-packages. config.json is
# bundled as data and resolved at runtime through pacman.paths.
from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("mazegenerator")

a = Analysis(
    ["pac-man.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("config.json", "."),
        ("PACKAGED_README.txt", "."),
    ],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="pacman42",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
