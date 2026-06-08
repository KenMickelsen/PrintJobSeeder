# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the PrinterLogic Output Demo on macOS.

Produces a proper .app bundle (double-clickable in Finder) at:
    dist/PrinterLogic Output Demo.app

Build with:
    pyinstaller PrinterLogicOutputDemo-Mac.spec

Notes:
  - --windowed (no terminal) is set via console=False / BUNDLE; this is
    the expected Mac GUI app behaviour.
  - Templates and reportlab data files are bundled for offline use.
  - Settings and logs are written to
    ~/Library/Application Support/PrinterLogicOutputDemo/ at runtime
    (see print_utils._base_dir).
  - To distribute without Gatekeeper warnings, sign with a Developer ID:
      codesign --deep -s "Developer ID Application: Your Name (TEAMID)" \
               "dist/PrinterLogic Output Demo.app"
    and notarise with notarytool before zipping/DMG-ing.
"""

from PyInstaller.utils.hooks import collect_all

# Bundle reportlab's data files (fonts, etc.) so PDF generation works.
reportlab_datas, reportlab_binaries, reportlab_hiddenimports = collect_all('reportlab')


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=reportlab_binaries,
    # Note: macOS uses ':' as the separator in --add-data; in a .spec file
    # the tuple form ('src', 'dest') is platform-neutral.
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
    [],
    exclude_binaries=True,   # binaries collected separately for .app bundle
    name='PrinterLogic Output Demo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX corrupts bundled Tcl/Tk on macOS -> rendering glitches
    console=False,           # no terminal window — standard Mac GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,    # avoid legacy Carbon argv emulation
    target_arch=None,        # None = build for host arch; set 'universal2' for fat binary
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,           # see note above — UPX is unsafe for the macOS Tk frameworks
    upx_exclude=[],
    name='PrinterLogic Output Demo',
)

app = BUNDLE(
    coll,
    name='PrinterLogic Output Demo.app',
    bundle_identifier='com.printerlogic.outputdemo',
    version='1.0.0',
    info_plist={
        'CFBundleDisplayName': 'PrinterLogic Output Demo',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        # Allows the app to make outbound network requests (local Flask servers).
        'NSAppTransportSecurity': {
            'NSAllowsLocalNetworking': True,
        },
    },
)
