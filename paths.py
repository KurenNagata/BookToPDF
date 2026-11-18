"""保存先の既定値と、フォルダ名の正規化。

GUI（main.py）と CaptureEngine の両方から使うので、tkinter にも mss にも
依存させない純粋ロジックに保つ。
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping

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


def owlbunko_library_dir(env: Mapping[str, str] | None = None,
                         home: str | None = None) -> str | None:
    """OwlBunko（本棚アプリ）の本棚フォルダ。使っていない・見つからなければ None。

    順に調べる: OwlBunko の設定（%APPDATA%\\OwlBunko\\settings.json の library_dir）
    → ~/OwlBunko（フォルダがあるとき）。どちらも、フォルダが実際にあるときだけ返す。
    フォルダは作らない（OwlBunko を使っていない人の動きを変えないため）。
    """
    env = os.environ if env is None else env
    home = os.path.expanduser('~') if home is None else home

    appdata = env.get('APPDATA')
    settings = os.path.join(appdata, 'OwlBunko', 'settings.json') if appdata else None
    if settings:
        try:
            with open(settings, encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = None
        configured = data.get('library_dir') if isinstance(data, dict) else None
        if isinstance(configured, str) and configured.strip():
            path = os.path.normpath(configured.strip())
            if os.path.isdir(path):
                return path

    fallback = os.path.join(home, 'OwlBunko')
    return os.path.normpath(fallback) if os.path.isdir(fallback) else None


def is_library_dir(path: str, library: str | None = None) -> bool:
    """path が OwlBunko の本棚フォルダか（大文字小文字・表記の違いは同じとみなす）。"""
    library = owlbunko_library_dir() if library is None else library
    if not path or not library:
        return False
    return os.path.normcase(os.path.abspath(path)) == os.path.normcase(
        os.path.abspath(library))


def default_output_dir() -> str:
    """既定の保存先。OwlBunko の本棚フォルダ、無ければダウンロードフォルダ、無ければホーム。"""
    library = owlbunko_library_dir()
    if library:
        return library
    home = os.path.expanduser('~')
    for candidate in (_downloads_from_registry(),
                      os.path.join(home, 'Downloads')):
        if candidate and os.path.isdir(candidate):
            return candidate
    return home
