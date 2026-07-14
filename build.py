"""配布物を一括生成する。

    python build.py                  保存先をダイアログで選ぶ（既定: dist）
    python build.py --out D:\\配布    ダイアログを出さず指定フォルダへ
    python build.py --no-ask         ダイアログを出さず dist へ

選んだフォルダに次の 2 つを出力する:
    BookToPDF.exe … Python 不要の単体実行ファイル
    使い方.pdf     … MANUAL.md から生成した利用者向けマニュアル

PDF は MANUAL.md を読んで作るので、使い方を書き換えたら build.py を流し直せば
exe とマニュアルの内容が必ず揃う。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / 'BookToPDF.spec'
MANUAL_SRC = ROOT / 'MANUAL.md'

DEFAULT_DIST = ROOT / 'dist'    # 保存先を選ばなかったときの既定
WORK_DIR = ROOT / 'build'       # PyInstaller の中間ファイル置き場（成果物ではない）

EXE_NAME = 'BookToPDF.exe'
MANUAL_NAME = '使い方.pdf'


def _step(message: str) -> None:
    print(f'\n=== {message} ===', flush=True)


def _ask_output_dir(default: Path) -> Path:
    """配布物の保存先をエクスプローラーで選んでもらう。

    キャンセルしたら既定 (dist) のまま進める。ビルドは数分かかるので、
    先に聞いてから走らせる。
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return default   # tkinter の無い環境ではダイアログを出さない

    root = tk.Tk()
    root.withdraw()
    try:
        chosen = filedialog.askdirectory(
            title='配布物 (BookToPDF.exe / 使い方.pdf) の保存先を選んでください',
            initialdir=str(default if default.is_dir() else ROOT),
        )
    finally:
        root.destroy()

    return Path(chosen) if chosen else default


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


def _build_exe(out_dir: Path) -> Path:
    _step('exe をビルドしています（数分かかります）')
    # spec には出力先を書かない。--distpath で毎回渡すことで、spec を書き換えずに
    # 保存先を変えられる（--workpath は中間ファイルを常にリポジトリ内に留める）。
    subprocess.run([sys.executable, '-m', 'PyInstaller', str(SPEC),
                    '--noconfirm',
                    '--distpath', str(out_dir),
                    '--workpath', str(WORK_DIR)],
                   check=True, cwd=ROOT)

    exe = out_dir / EXE_NAME
    if not exe.exists():
        raise SystemExit(f'ビルドは終了しましたが {exe} が見つかりません')
    return exe


def _build_manual(out_dir: Path) -> Path:
    _step('使い方 PDF を生成しています')
    # exe ビルド後に import する（PyInstaller の解析対象に入れないため）
    from manual_pdf import build_manual_pdf

    manual_pdf = out_dir / MANUAL_NAME
    build_manual_pdf(str(MANUAL_SRC), str(manual_pdf))
    return manual_pdf


def _mb(path: Path) -> str:
    return f'{path.stat().st_size / 1024 / 1024:.1f} MB'


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='配布物 (exe + 使い方 PDF) を作る')
    parser.add_argument('--out', metavar='フォルダ',
                        help='配布物の保存先。省略すると選択ダイアログを出す')
    parser.add_argument('--no-ask', action='store_true',
                        help=f'ダイアログを出さず {DEFAULT_DIST.name} に出力する')
    return parser.parse_args()


def _resolve_output_dir(args: argparse.Namespace) -> Path:
    if args.out:
        return Path(args.out).expanduser().resolve()
    if args.no_ask:
        return DEFAULT_DIST
    return _ask_output_dir(DEFAULT_DIST).resolve()


def main() -> None:
    args = _parse_args()

    if not SPEC.exists():
        raise SystemExit(f'{SPEC} がありません')
    if not MANUAL_SRC.exists():
        raise SystemExit(f'{MANUAL_SRC} がありません')

    out_dir = _resolve_output_dir(args)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SystemExit(f'保存先フォルダを作れません: {out_dir}\n{exc}')
    print(f'保存先: {out_dir}')

    _ensure_pyinstaller()
    exe = _build_exe(out_dir)
    manual_pdf = _build_manual(out_dir)

    _step('完成')
    print(f'{exe}    ({_mb(exe)})')
    print(f'{manual_pdf}  ({_mb(manual_pdf)})')
    print('\nこの 2 ファイルをまとめて配布すれば、'
          'Python の無い Windows でもそのまま使えます。')


if __name__ == '__main__':
    main()
