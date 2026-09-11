# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: un solo SaxonRunner.exe, senza console.
#   python -m PyInstaller --noconfirm --clean SaxonRunner.spec

a = Analysis(
    ['SaxonRunner.pyw'],
    pathex=[],
    binaries=[],
    # L'icona serve anche a runtime, per la barra del titolo di Tk.
    datas=[('assets/SaxonRunner.ico', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SaxonRunner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX e' fra le cause piu' frequenti di falsi positivi degli antivirus
    # sugli eseguibili PyInstaller: meglio qualche MB in piu'.
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/SaxonRunner.ico'],
)
