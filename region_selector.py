"""キャプチャ範囲選択オーバーレイ。

全画面の半透明 Toplevel を出し、左ドラッグで矩形を選ばせる。
戻り値は mss にそのまま渡せる {'left','top','width','height'}（物理 px）。

座標の扱い（重要）:
  - 描画には event.x / event.y（キャンバス座標）
  - 戻り値には event.x_root / event.y_root（スクリーン物理座標）
  main.py で DPI awareness を設定済みのため、両者はプライマリモニタ上で一致する。
"""

from __future__ import annotations

import tkinter as tk

ACCENT = '#00e5ff'      # 選択枠のシアン
INK = '#0b0e12'
HINT_BG = '#0b0e12'
HINT_FG = '#e9eef4'

MIN_SIZE = 5            # 5px 以下のドラッグは無効


class RegionSelector:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._region: dict | None = None

        self._win: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._rect = None
        self._badge = None
        self._badge_bg = None

        self._start_canvas: tuple[int, int] | None = None
        self._start_screen: tuple[int, int] | None = None

    # ------------------------------------------------------------------ public
    def select(self) -> dict | None:
        """モーダルで範囲選択させる。Esc または無効な選択でキャンセル → None。"""
        self._region = None

        win = tk.Toplevel(self.root)
        self._win = win
        win.attributes('-fullscreen', True)
        win.attributes('-alpha', 0.25)
        win.attributes('-topmost', True)
        win.configure(bg=INK, cursor='crosshair')

        canvas = tk.Canvas(win, bg=INK, highlightthickness=0, cursor='crosshair')
        canvas.pack(fill='both', expand=True)
        self._canvas = canvas

        self._draw_hint(canvas)

        canvas.bind('<Button-1>', self._on_press)
        canvas.bind('<B1-Motion>', self._on_drag)
        canvas.bind('<ButtonRelease-1>', self._on_release)
        win.bind('<Escape>', lambda _e: self._cancel())
        canvas.bind('<Escape>', lambda _e: self._cancel())

        win.focus_force()
        canvas.focus_set()
        win.grab_set()
        self.root.wait_window(win)

        return self._region

    # ----------------------------------------------------------------- drawing
    def _draw_hint(self, canvas: tk.Canvas) -> None:
        """画面上部に操作ヒントを出す。"""
        screen_w = self.root.winfo_screenwidth()
        cx, cy = screen_w // 2, 64

        text = 'ドラッグでキャプチャ範囲を選択    Esc でキャンセル'
        label = canvas.create_text(
            cx, cy, text=text, fill=HINT_FG,
            font=('Segoe UI', 13), anchor='center',
        )
        x1, y1, x2, y2 = canvas.bbox(label)
        pad_x, pad_y = 22, 12
        bg = canvas.create_rectangle(
            x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y,
            fill=HINT_BG, outline=ACCENT, width=1,
        )
        canvas.tag_lower(bg, label)

    def _update_badge(self, x: int, y: int, w: int, h: int) -> None:
        """ドラッグ中の矩形に寸法バッジ（等幅）を添える。"""
        canvas = self._canvas
        for item in (self._badge_bg, self._badge):
            if item is not None:
                canvas.delete(item)

        # 矩形の左上外側。画面上端に近ければ内側へ逃がす。
        bx, by = x, y - 16
        anchor = 'sw'
        if by < 24:
            by = y + h + 16
            anchor = 'nw'

        self._badge = canvas.create_text(
            bx, by, text=f'{w} x {h}', fill=ACCENT,
            font=('Consolas', 11, 'bold'), anchor=anchor,
        )
        x1, y1, x2, y2 = canvas.bbox(self._badge)
        self._badge_bg = canvas.create_rectangle(
            x1 - 8, y1 - 5, x2 + 8, y2 + 5, fill=INK, outline='',
        )
        canvas.tag_lower(self._badge_bg, self._badge)

    # ---------------------------------------------------------------- handlers
    def _on_press(self, event) -> None:
        self._start_canvas = (event.x, event.y)
        self._start_screen = (event.x_root, event.y_root)

        canvas = self._canvas
        if self._rect is not None:
            canvas.delete(self._rect)
        self._rect = canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline=ACCENT, width=2,
        )

    def _on_drag(self, event) -> None:
        if self._start_canvas is None:
            return
        x0, y0 = self._start_canvas
        self._canvas.coords(self._rect, x0, y0, event.x, event.y)

        left, top = min(x0, event.x), min(y0, event.y)
        width, height = abs(event.x - x0), abs(event.y - y0)
        self._update_badge(left, top, width, height)

    def _on_release(self, event) -> None:
        if self._start_screen is None:
            return
        x0, y0 = self._start_screen
        x1, y1 = event.x_root, event.y_root

        left, top = min(x0, x1), min(y0, y1)
        width, height = abs(x1 - x0), abs(y1 - y0)

        # 小さすぎる選択は無効。オーバーレイは閉じず、選択を続けさせる。
        if width <= MIN_SIZE or height <= MIN_SIZE:
            self._reset_shapes()
            return

        self._region = {
            'left': int(left),
            'top': int(top),
            'width': int(width),
            'height': int(height),
        }
        self._close()

    def _reset_shapes(self) -> None:
        canvas = self._canvas
        for item in (self._rect, self._badge, self._badge_bg):
            if item is not None:
                canvas.delete(item)
        self._rect = self._badge = self._badge_bg = None
        self._start_canvas = self._start_screen = None

    def _cancel(self) -> None:
        self._region = None
        self._close()

    def _close(self) -> None:
        if self._win is not None:
            self._win.grab_release()
            self._win.destroy()
            self._win = None
