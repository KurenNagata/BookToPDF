"""保存先の既定値と、フォルダ名の正規化。

GUI（main.py）と CaptureEngine の両方から使うので、tkinter にも mss にも
依存させない純粋ロジックに保つ。
"""

from __future__ import annotations

import os
import time

# Windows がフォルダ名に使えない文字
INVALID_NAME_CHARS = '<>:"/\\|?*'

# Windows の予約デバイス名。この名前のフォルダは作れない。
_RESERVED_NAMES = (
    {'CON', 'PRN', 'AUX', 'NUL'}
    | {f'COM{i}' for i in range(1, 10)}
    | {f'LPT{i}' for i in range(1, 10)}
)

# 長すぎる名前はパス長 (260) を圧迫し、中の page_0001.png が作れなくなる
MAX_NAME_LENGTH = 100

# 「ダウンロード」フォルダはユーザーが移動できるため、~/Downloads を決め打ちに
# せずレジストリの実パスを引く。キー名は KnownFolderID (FOLDERID_Downloads)。
_DOWNLOADS_GUID = '{374DE290-123F-4565-9164-39C4925E467B}'
_SHELL_FOLDERS_KEY = (
    r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
)


def timestamp_folder_name() -> str:
    """フォルダ名を指定しなかったときの既定名。"""
    return time.strftime('capture_%Y%m%d_%H%M%S')


def sanitize_folder_name(name: str | None) -> str:
    """入力されたフォルダ名を、Windows で実際に作れる形に直す。

    使えない文字は _ に置き換える。末尾の空白と '.' は Windows が黙って落とす
    （'章1.' で作ると '章1' になる）ため、こちらで先に落としておく。
    名前として成立しなくなった場合は '' を返す（呼び出し側で既定名にする）。
    """
    if not name:
        return ''

    cleaned = ''.join(
        '_' if (ch in INVALID_NAME_CHARS or ord(ch) < 32) else ch
        for ch in name
    )
    cleaned = cleaned.strip().rstrip('. ')
    if not cleaned:
        return ''

    # 'NUL' や 'con.txt' のような予約名はフォルダにできない
    if cleaned.split('.')[0].upper() in _RESERVED_NAMES:
        cleaned = f'_{cleaned}'

    return cleaned[:MAX_NAME_LENGTH].rstrip('. ')


def _downloads_from_registry() -> str | None:
    try:
        import winreg   # Windows 以外には無い
    except ImportError:
        return None

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SHELL_FOLDERS_KEY) as key:
            path, _ = winreg.QueryValueEx(key, _DOWNLOADS_GUID)
    except OSError:
        return None

    return os.path.normpath(os.path.expandvars(path)) if path else None


def default_output_dir() -> str:
    """既定の保存先。ダウンロードフォルダ、無ければホーム。"""
    home = os.path.expanduser('~')
    for candidate in (_downloads_from_registry(),
                      os.path.join(home, 'Downloads')):
        if candidate and os.path.isdir(candidate):
            return candidate
    return home
