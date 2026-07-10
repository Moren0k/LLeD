# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: congela el backend (servidor.py) en modo onedir.

Genera dist_backend/servidor/servidor.exe con todo lo necesario para correr sin
Python instalado en la máquina destino (Windows 10/11).
"""

from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
)

hiddenimports = []
for paquete in ("sklearn", "scipy", "numpy", "spotipy", "bleak",
                "bleak.backends.winrt", "winrt"):
    hiddenimports += collect_submodules(paquete)
hiddenimports += collect_submodules("mss")
hiddenimports += [
    "pyaudiowpatch",
    "websockets",
    "joblib",
    "sklearn.utils._typedefs",
    "sklearn.neighbors._partition_nodes",
    "sklearn.tree._utils",
    "sklearn.utils._cython_blas",
]

datas = [("motor_visual.js", ".")]
datas += collect_data_files("sklearn")
datas += collect_data_files("scipy")
datas += collect_data_files("certifi")

binaries = []
for paquete in ("scipy", "numpy", "sklearn", "pyaudiowpatch"):
    binaries += collect_dynamic_libs(paquete)

a = Analysis(
    ["servidor.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest", "PyQt5", "PySide6", "IPython", "notebook"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="servidor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # NO comprimir DLLs científicas
    console=True,       # stderr/stdout van a los pipes de Electron
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="servidor",
)
