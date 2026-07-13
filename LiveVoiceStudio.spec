# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

customtkinter_datas, customtkinter_binaries, customtkinter_hidden = collect_all("customtkinter")

hiddenimports = (
    customtkinter_hidden
    + collect_submodules("TikTokLive")
    + collect_submodules("edge_tts")
)

analysis = Analysis(
    ["main.py"],
    pathex=[],
    binaries=customtkinter_binaries,
    datas=customtkinter_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "sklearn",
        "seaborn",
        "jupyter",
        "IPython",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="LiveVoiceStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
