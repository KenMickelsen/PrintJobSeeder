# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the Vasion Output Demo Launcher.

Builds a single-file Windows executable (PrinterLogicOutputDemo.exe) that bundles the
launcher, both Flask apps, the templates, and reportlab's data files.

Build with:
    pyinstaller PrinterLogicOutputDemo.spec
"""

from PyInstaller.utils.hooks import collect_all

# Bundle reportlab's data files (fonts, etc.) so PDF generation works.
reportlab_datas, reportlab_binaries, reportlab_hiddenimports = collect_all('reportlab')


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=reportlab_binaries,
    datas=[('templates', 'templates')] + reportlab_datas,
    hiddenimports=reportlab_hiddenimports,
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
    name='PrinterLogicOutputDemo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # no console by default; pass --console at runtime to get one
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
