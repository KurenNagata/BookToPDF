"""配布物を一括生成する。

    python build.py

dist/ に次の 2 つを出力する:
    BookToPDF.exe … Python 不要の単体実行ファイル
    使い方.pdf     … README.md から生成した利用者向けマニュアル

PDF は README.md を読んで作るので、使い方を書き換えたら build.py を流し直せば
exe とマニュアルの内容が必ず揃う。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / 'BookToPDF.spec'
README = ROOT / 'README.md'
DIST = ROOT / 'dist'
EXE = DIST / 'BookToPDF.exe'
MANUAL = DIST / '使い方.pdf'


def _step(message: str) -> None:
    print(f'\n=== {message} ===', flush=True)


def _ensure_pyinstaller() -> None:
    """PyInstaller は実行時のみ必要なので、無ければその場で入れる。"""
    try:
        import PyInstaller  # noqa: F401
        return
    except ImportError:
        pass

    _step('PyInstaller をインストールしています')
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
                   check=True)


def _build_exe() -> None:
    _step('exe をビルドしています（数分かかります）')
    subprocess.run([sys.executable, '-m', 'PyInstaller',
                    str(SPEC), '--noconfirm'],
                   check=True, cwd=ROOT)

    if not EXE.exists():
        raise SystemExit(f'ビルドは終了しましたが {EXE} が見つかりません')


def _build_manual() -> None:
    _step('使い方 PDF を生成しています')
    # exe ビルド後に import する（PyInstaller の解析対象に入れないため）
    from manual_pdf import build_manual_pdf

    DIST.mkdir(exist_ok=True)
    build_manual_pdf(str(README), str(MANUAL))


def _mb(path: Path) -> str:
    return f'{path.stat().st_size / 1024 / 1024:.1f} MB'


def main() -> None:
    if not SPEC.exists():
        raise SystemExit(f'{SPEC} がありません')
    if not README.exists():
        raise SystemExit(f'{README} がありません')

    _ensure_pyinstaller()
    _build_exe()
    _build_manual()

    _step('完成')
    print(f'{EXE}    ({_mb(EXE)})')
    print(f'{MANUAL}  ({_mb(MANUAL)})')
    print('\nこの 2 ファイルをまとめて配布すれば、'
          'Python の無い Windows でもそのまま使えます。')


if __name__ == '__main__':
    main()
