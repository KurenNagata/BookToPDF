"""キャプチャループ本体。

ワーカースレッドで run() を回し、進捗は on_status / on_progress、
終了は on_done で呼び出し側（GUI）に返す。
tkinter ウィジェットはここから絶対に触らない（main.py 側で after(0, ...) に委譲）。
"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
import time
from typing import Callable

import mss
from PIL import Image
from pynput.keyboard import Controller, Key, Listener

from pdf_builder import build_pdf

DIRECTION_KEYS: dict[str, Key | None] = {
    '右 (→)': Key.right,
    '左 (←)': Key.left,
    '下 (↓)': Key.down,
    'なし（手動でめくる）': None,
}

# 出力形式 → 保存する成果物
OUTPUT_MODES: dict[str, tuple[str, ...]] = {
    'PDF + 画像 (PNG)': ('pdf', 'png'),
    'PDFのみ': ('pdf',),
    '画像 (PNG) のみ': ('png',),
}

PDF_FILENAME = 'capture.pdf'

SIG_SIZE = (32, 32)

# --- ページ送りの考え方 -------------------------------------------------------
# 「キーを送る → 決め打ちの時間だけ待つ → 撮る」だと、次の 3 つで簡単に失敗する。
#   1. 描画が待ち時間に間に合わない → 前のページを撮ってしまう
#   2. キーがビューアーに届かない（取りこぼし）→ ページが進まない
#   3. 似たページ（箇条書きが 1 行増えるだけ等）を「変わっていない」と誤判定
#      → キーを再送してしまい、実際は進んでいるページを撮らずに飛ばす
# 1・2 は「画面が実際に変わるまで待ち、変わらなければ再送する」で対処する。
# 3 は判定方式で対処する: 画像全体の平均差は似たページで 0 に近づくため、
# 「一定以上変化した画素の割合」で判定する（局所的な変化も確実に拾える）。
KEY_HOLD = 0.05          # キーを押している時間 (秒)。0 だと取りこぼすアプリがある
POLL_INTERVAL = 0.12     # 画面が変わったか確認する間隔 (秒)
CHANGE_TIMEOUT = 2.5     # これだけ変化がなければキーを再送する (秒)
MAX_KEY_RESENDS = 2      # キーの再送回数
STABLE_TIMEOUT = 2.0     # 変化検知後、描画が落ち着つくのを待つ上限 (秒)
CHANGE_RATIO = 0.004     # 変化した画素がこの割合以上で「ページが変わった」とみなす

# mss 10 系で mss.mss() は非推奨。新旧どちらでも動くように解決しておく。
_mss_open = getattr(mss, 'MSS', None) or mss.mss


def primary_monitor_region() -> dict:
    """プライマリモニタ全体を region 形式で返す（全画面キャプチャ用）。"""
    with _mss_open() as sct:
        monitor = sct.monitors[1]
    return {
        'left': int(monitor['left']),
        'top': int(monitor['top']),
        'width': int(monitor['width']),
        'height': int(monitor['height']),
    }


def fingerprint(image: Image.Image) -> list[int]:
    """32x32 グレースケールのバイト列を指紋にする。

    Image.getdata() は非推奨のため tobytes() を使う。
    """
    return list(image.convert('L').resize(SIG_SIZE).tobytes())


def signature_diff(a: list[int] | None, b: list[int] | None) -> float:
    """指紋の平均絶対差。0 = 完全一致。どちらかが None なら 255.0。"""
    if a is None or b is None:
        return 255.0
    return sum(abs(p - q) for p, q in zip(a, b)) / len(a)


def changed_fraction(a: list[int] | None, b: list[int] | None,
                     delta: int = 6) -> float:
    """delta より大きく変化した画素の割合 (0.0〜1.0)。どちらかが None なら 1.0。

    平均差 (signature_diff) は似たページ同士で 0 に近づくため、
    「ページが変わったか」の判定にはこちらを使う。カーソル点滅や
    アンチエイリアスの揺らぎは delta 以下の微小変化として除外される。
    """
    if a is None or b is None:
        return 1.0
    changed = sum(1 for p, q in zip(a, b) if abs(p - q) > delta)
    return changed / len(a)


class CaptureEngine:
    def __init__(self, config: dict,
                 on_status: Callable[[str], None],
                 on_done: Callable[[str | None], None],
                 on_progress: Callable[[int, int], None] | None = None):
        self.config = config
        self.on_status = on_status
        self.on_done = on_done
        self.on_progress = on_progress or (lambda page, total: None)
        self._stop = threading.Event()
        # 重複検知しきい値は「変化とみなす画素差」に対応させる。
        # 大きくするほど変化を拾いにくくなる = 止まりやすくなる（従来と同じ向き）
        self._delta = max(2, round(float(config.get('dup_threshold', 3)) * 2))

    def stop(self) -> None:
        """中断要求。ループ・待機・カウントダウンは即座に抜ける。"""
        self._stop.set()

    # --------------------------------------------------------------- internals
    def _on_key(self, key) -> None:
        if key == Key.esc:
            self._stop.set()

    def _grab(self, sct, region: dict) -> tuple[Image.Image, list[int]]:
        raw = sct.grab(region)
        image = Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX')
        return image, fingerprint(image)

    def _page_changed(self, sig: list[int] | None, base: list[int] | None) -> bool:
        return changed_fraction(sig, base, self._delta) >= CHANGE_RATIO

    def _send_key(self, keyboard: Controller, key: Key) -> None:
        """ページ送りキーを 1 回送る。

        press/release を間髪入れずに呼ぶと入力を取りこぼすアプリがあるため、
        実際のキー操作と同じように少しだけ押し続ける。
        """
        keyboard.press(key)
        time.sleep(KEY_HOLD)
        keyboard.release(key)

    def _await_page_change(self, sct, region: dict, keyboard: Controller,
                           key: Key, last_sig: list[int] | None,
                           min_wait: float):
        """キーを送った後、ページが実際に変わるのを待つ。

        変わらなければキーを再送する（取りこぼし対策）。規定回数送っても
        変わらなければ末尾に到達したと判断する。

        戻り値: (image, sig)。末尾または中断なら (None, None)。
        """
        if min_wait > 0 and self._stop.wait(min_wait):
            return None, None

        for attempt in range(MAX_KEY_RESENDS + 1):
            deadline = time.monotonic() + CHANGE_TIMEOUT
            while time.monotonic() < deadline:
                image, sig = self._grab(sct, region)
                if self._page_changed(sig, last_sig):
                    return self._wait_render_settled(sct, region, image, sig)
                if self._stop.wait(POLL_INTERVAL):
                    return None, None

            if attempt < MAX_KEY_RESENDS:
                self.on_status(
                    f'ページが変わりません。キーを送り直しています… '
                    f'({attempt + 1}/{MAX_KEY_RESENDS})'
                )
                self._send_key(keyboard, key)

        return None, None

    def _wait_render_settled(self, sct, region: dict, image, sig):
        """ページの変化を検知した後、描画が落ち着くまで待って撮り直す。

        めくりアニメーションやフェードの途中を保存しないためのもの。
        2 回連続でほぼ同じ画面になったら「描画完了」とみなす。
        """
        deadline = time.monotonic() + STABLE_TIMEOUT
        while time.monotonic() < deadline:
            if self._stop.wait(POLL_INTERVAL):
                return None, None
            nxt_image, nxt_sig = self._grab(sct, region)
            if not self._page_changed(nxt_sig, sig):
                return nxt_image, nxt_sig
            image, sig = nxt_image, nxt_sig
        return image, sig   # 動き続ける場合（動画等）は打ち切って採用する

    def _countdown(self, seconds: int) -> None:
        for remaining in range(seconds, 0, -1):
            if self._stop.is_set():
                return
            self.on_status(
                f'{remaining} 秒後に開始… 取り込みたいビューアーを前面にしてください'
            )
            # Event.wait なら Esc で即座に抜けられる（time.sleep だと待たされる）
            if self._stop.wait(1.0):
                return

    def _make_output_dir(self, base: str) -> str:
        """保存先フォルダ（base/capture_日時）を作って返す。

        exist_ok=False + FileExistsError で作成し、確認してから作る方式は取らない
        （確認と作成の間に他プロセスが作る可能性があるため）。
        """
        name = time.strftime('capture_%Y%m%d_%H%M%S')
        for suffix in range(1, 100):
            candidate = os.path.join(
                base, name if suffix == 1 else f'{name}_{suffix}')
            try:
                os.makedirs(candidate)
                return candidate
            except FileExistsError:
                continue   # 同じ秒に複数回開始した場合
        raise OSError(f'保存先フォルダを作成できません: {base}')

    # -------------------------------------------------------------------- main
    def run(self) -> None:
        cfg = self.config
        region = cfg['region']
        direction_key = DIRECTION_KEYS.get(cfg['direction'])
        page_delay = cfg['page_delay'] / 1000.0
        max_pages = int(cfg['max_pages'])
        start_delay = int(cfg['start_delay'])
        outputs = OUTPUT_MODES.get(cfg.get('output_mode'), ('pdf',))

        keyboard = Controller()
        listener = Listener(on_press=self._on_key)
        listener.start()

        work_dir: str | None = None
        saved: list[str] = []
        keep_work_dir = False

        try:
            self._countdown(start_delay)

            work_dir = tempfile.mkdtemp(prefix='snap2pdf_pages_')
            last_sig: list[int] | None = None
            page = 0

            with _mss_open() as sct:
                while page < max_pages:
                    if self._stop.is_set():
                        self.on_status(f'中断しました（{len(saved)} ページ取得済み）')
                        break

                    if page == 0:
                        # 1 ページ目は今表示されている画面をそのまま撮る
                        image, sig = self._grab(sct, region)

                    elif direction_key is None:
                        # 手動モード: 一定間隔で撮り続ける（重複検知は行わない）
                        if self._stop.wait(page_delay):
                            continue
                        image, sig = self._grab(sct, region)

                    else:
                        # 自動モード: キーを送り、実際にページが変わるまで待つ
                        self._send_key(keyboard, direction_key)
                        image, sig = self._await_page_change(
                            sct, region, keyboard, direction_key,
                            last_sig, page_delay)

                        if image is None:
                            if self._stop.is_set():
                                self.on_status(
                                    f'中断しました（{len(saved)} ページ取得済み）')
                            else:
                                self.on_status(
                                    'ページが変わらなくなりました → 末尾と判断して'
                                    '停止しました')
                            break

                    page += 1
                    path = os.path.join(work_dir, f'page_{page:04d}.png')
                    image.save(path, 'PNG')
                    saved.append(path)
                    last_sig = sig

                    self.on_status(f'{page} ページ目を取得')
                    self.on_progress(page, max_pages)

            if not saved:
                self.on_status('取得ページがありません')
                self.on_done(None)
                return

            # ---- 保存: base/capture_日時/ に PDF・PNG をまとめる ----
            out_dir = self._make_output_dir(cfg['output_base'])
            png_saved = False

            if 'png' in outputs:
                self.on_status(f'{len(saved)} 枚のページ画像を保存中…')
                for path in saved:
                    shutil.copy2(path, out_dir)
                png_saved = True

            if 'pdf' in outputs:
                self.on_status(f'{len(saved)} ページを PDF に変換中…')
                try:
                    build_pdf(saved, os.path.join(out_dir, PDF_FILENAME),
                              cfg['quality'])
                except Exception as exc:  # noqa: BLE001 - アプリは落とさない
                    # PDF に失敗しても撮ったページは失わせない:
                    # PNG をフォルダに退避してから知らせる
                    if not png_saved:
                        try:
                            for path in saved:
                                shutil.copy2(path, out_dir)
                            png_saved = True
                        except OSError:
                            keep_work_dir = True
                            self.on_status(f'PDF作成に失敗: {exc}\n'
                                           f'取得済み画像: {work_dir}')
                            self.on_done(None)
                            return
                    self.on_status(f'PDF作成に失敗: {exc}\n'
                                   f'ページ画像を保存しました: {out_dir}')
                    self.on_done(out_dir)
                    return

            self.on_status(f'完成: {out_dir}')
            self.on_done(out_dir)

        except Exception as exc:  # noqa: BLE001
            # ここで受け止めないとワーカースレッドが黙って死に、on_done が
            # 呼ばれず UI が「実行中」のまま固まる（開始ボタンが戻らない）。
            # 保存先の作成失敗・ディスク満杯・キャプチャ失敗などが該当する。
            if saved and work_dir:
                keep_work_dir = True   # 撮ったページは捨てない
                self.on_status(f'エラーが発生しました: {exc}\n'
                               f'取得済み画像: {work_dir}')
            else:
                self.on_status(f'エラーが発生しました: {exc}')
            self.on_done(None)

        finally:
            listener.stop()
            if work_dir and not keep_work_dir:
                shutil.rmtree(work_dir, ignore_errors=True)
