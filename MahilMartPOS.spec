# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, collect_submodules

datas = [('MahilMartPOS_App\\templates', 'MahilMartPOS_App\\templates'), ('staticfiles', 'staticfiles'), ('MahilMartPOS', 'MahilMartPOS'), ('MahilMartPOS_App', 'MahilMartPOS_App')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('django')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('barcode')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('psycopg2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pyodbc')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pymongo')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('dns')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
hiddenimports += [
    'win32print',
    'win32api',
    'win32con',
    'win32ui',
    'pywintypes',
    'pythoncom',
]
hiddenimports += collect_submodules('win32com')
binaries += collect_dynamic_libs('pywin32_system32')

icon_path = os.path.join('assets', 'branding', 'app.ico')
if not os.path.exists(icon_path):
    icon_path = None


a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['sqlite3', '_sqlite3', 'django.db.backends.sqlite3'],
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
    name='MahilMartPOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
