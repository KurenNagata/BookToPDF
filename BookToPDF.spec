# -*- mode: python ; coding: utf-8 -*-
r"""PyInstaller ビルド設定。

通常は `python build.py`（exe + 使い方 PDF を一括生成）を使う。
exe だけを作りたいときは:

  .venv\Scripts\activate
  pyinstaller BookToPDF.spec --noconfirm

生成物: dist\BookToPDF.exe（単一ファイル / コンソール非表示）
"""

# pynput は実行時にプラットフォーム別バックエンドを動的 import するため、
# 静的解析では追跡できない。Windows 向けバックエンドを明示する。
hiddenimports = [
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'pynput._util.win32',
]

# アプリが使わない開発用・重量級パッケージを除外してサイズを抑える。
excludes = [
    'pytest', 'pip_audit', 'lxml', 'numpy', 'setuptools', 'pip',
    'tkinter.test', 'test', 'unittest',
]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='BookToPDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,  # GUI アプリなのでコンソールウィンドウを出さない
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
