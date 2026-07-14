"""画面キャプチャ → PDF : エントリポイント + GUI。

python main.py で起動する。
"""

from __future__ import annotations

# --- 高 DPI 対応: tkinter を import / 初期化するより前に実行する ----------------
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
except Exception:
    pass  # 古い環境では失敗してもよい
# -----------------------------------------------------------------------------

import os
import threading
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

from capture_engine import (DIRECTION_KEYS, OUTPUT_MODES, CaptureEngine,
                            primary_monitor_region)
from paths import (INVALID_NAME_CHARS, default_output_dir,
                   sanitize_folder_name)
from pdf_builder import QUALITY_CHOICES, QUALITY_HIGH
from region_selector import RegionSelector

APP_TITLE = '画面キャプチャ → PDF'

# --- デザイントークン ---------------------------------------------------------
INK = '#111418'          # 主要テキスト
MUTED = '#6b7480'        # 補助テキスト
PAPER = '#eef1f5'        # ウィンドウ背景
CARD = '#ffffff'         # 入力欄・カード面
RULE = '#dbe0e7'         # 罫線
ACCENT = '#0066cc'       # 主アクション / ステータス
ACCENT_DARK = '#00509e'
OK = '#0a7a44'
ERROR = '#c0392b'

READOUT_BG = '#111418'   # 計器パネル（このアプリの主役）
READOUT_FG = '#00e5ff'
READOUT_DIM = '#5b6672'
READOUT_TROUGH = '#252c35'

# 操作系は Segoe UI、座標やページ数などの「データ」は等幅で出し分ける
UI_FAMILY = 'Segoe UI'
MONO_FAMILY = 'Consolas'

# --- 既定値 -------------------------------------------------------------------
DEFAULT_PAGE_DELAY = 300   # 最短待機。以降はページが変わるまで自動で待つ
DEFAULT_MAX_PAGES = 500
DEFAULT_DUP_THRESHOLD = 3
DEFAULT_START_DELAY = 4
DEFAULT_OUTPUT_DIR = default_output_dir()
DEFAULT_OUTPUT_MODE = 'PDF + 画像 (PNG)'

BASE_W, BASE_H = 470, 672   # 100% 表示スケール時のウィンドウサイズ


class Tooltip:
    """パラメータの意味をその場で説明する軽量ツールチップ。"""

    def __init__(self, widget: tk.Widget, text: str, font, wraplength: int,
                 delay: int = 450):
        self.widget = widget
        self.text = text
        self.font = font
        self.wraplength = wraplength
        self.delay = delay
        self._after_id: str | None = None
        self._tip: tk.Toplevel | None = None

        widget.bind('<Enter>', self._schedule, add='+')
        widget.bind('<Leave>', self._hide, add='+')
        widget.bind('<ButtonPress>', self._hide, add='+')

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        if self._tip is not None:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6

        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f'+{x}+{y}')
        tip.configure(bg=RULE)
        tk.Label(
            tip, text=self.text, justify='left', bg=INK, fg='#e9eef4',
            font=self.font, padx=10, pady=6, wraplength=self.wraplength,
        ).pack(padx=1, pady=1)
        self._tip = tip

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


class Readout(tk.Frame):
    """計器パネル。範囲・取得ページ数・進捗を 1 枚にまとめて見せる。

    進捗は下端 3px のラインで表す（独立したプログレスバーを置くより情報が集まる）。
    """

    def __init__(self, parent, px, fonts):
        super().__init__(parent, bg=READOUT_BG)
        self._px = px

        body = tk.Frame(self, bg=READOUT_BG)
        body.pack(fill='x')

        self.region_label = tk.Label(
            body, text='範囲: 未選択', bg=READOUT_BG, fg=READOUT_DIM,
            font=fonts['mono'], anchor='w', padx=px(14), pady=px(9),
        )
        self.region_label.pack(side='left')

        self.counter_label = tk.Label(
            body, text='—', bg=READOUT_BG, fg=READOUT_DIM,
            font=fonts['mono_sm'], anchor='e', padx=px(14),
        )
        self.counter_label.pack(side='right')

        # width=1: Canvas の既定幅(378px)にレイアウトを引っ張られないようにする
        self.bar = tk.Canvas(self, height=px(3), width=1, bg=READOUT_TROUGH,
                             highlightthickness=0)
        self.bar.pack(fill='x')
        self._fill = self.bar.create_rectangle(0, 0, 0, px(3), fill=READOUT_FG,
                                               outline='')
        self._fraction = 0.0
        self.bar.bind('<Configure>', lambda _e: self._redraw())

    def _redraw(self) -> None:
        width = self.bar.winfo_width() * self._fraction
        self.bar.coords(self._fill, 0, 0, width, self._px(3))

    def set_region(self, region: dict | None) -> None:
        if region is None:
            self.region_label.configure(text='範囲: 未選択', fg=READOUT_DIM)
        else:
            self.region_label.configure(
                text='範囲: {width}×{height} @ ({left},{top})'.format(**region),
                fg=READOUT_FG,
            )

    def set_progress(self, page: int | None, total: int | None) -> None:
        if page is None or not total:
            self.counter_label.configure(text='—', fg=READOUT_DIM)
            self._fraction = 0.0
        else:
            self.counter_label.configure(text=f'{page} / {total}', fg=READOUT_FG)
            self._fraction = min(1.0, page / total)
        self._redraw()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.region: dict | None = None
        self.engine: CaptureEngine | None = None
        self.running = False

        # 表示スケール係数。tk の scaling は「1pt あたりの px」で、96dpi(100%) で 1.333。
        # ポイント指定のフォントは DPI で自動拡大されるので、ウィンドウ・余白も
        # 同じ係数で拡大し、レイアウトが崩れないようにする。
        self.scale = float(root.tk.call('tk', 'scaling')) / (96 / 72)
        self._init_fonts()

        root.title(APP_TITLE)
        root.resizable(False, False)
        root.configure(bg=PAPER)
        self._center()

        self._init_styles()
        self._build_ui()
        self._set_status('準備完了', 'info')

        root.protocol('WM_DELETE_WINDOW', self._on_close)

    # ------------------------------------------------------------------- setup
    def px(self, value: float) -> int:
        """100% 表示スケール基準の px を、実際の表示スケールに合わせる。"""
        return max(1, round(value * self.scale))

    def _init_fonts(self) -> None:
        self.fonts = {
            'title': tkfont.Font(family=UI_FAMILY, size=14, weight='bold'),
            'ui': tkfont.Font(family=UI_FAMILY, size=10),
            'ui_sm': tkfont.Font(family=UI_FAMILY, size=9),
            'step': tkfont.Font(family=UI_FAMILY, size=9, weight='bold'),
            'btn': tkfont.Font(family=UI_FAMILY, size=10, weight='bold'),
            'mono': tkfont.Font(family=MONO_FAMILY, size=10),
            'mono_sm': tkfont.Font(family=MONO_FAMILY, size=9),
        }

    def _center(self) -> None:
        w, h = self.px(BASE_W), self.px(BASE_H)
        x = (self.root.winfo_screenwidth() - w) // 2
        y = max(0, (self.root.winfo_screenheight() - h) // 2 - self.px(30))
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def _init_styles(self) -> None:
        px = self.px
        style = ttk.Style()
        style.theme_use('clam')  # 配色を自前で決められるテーマ

        style.configure('TFrame', background=PAPER)

        style.configure('Step.TLabel', background=PAPER, foreground=MUTED,
                        font=self.fonts['step'])
        style.configure('Field.TLabel', background=PAPER, foreground=INK,
                        font=self.fonts['ui_sm'])
        style.configure('Unit.TLabel', background=PAPER, foreground=MUTED,
                        font=self.fonts['ui_sm'])

        style.configure('Primary.TButton', background=ACCENT, foreground='#ffffff',
                        font=self.fonts['btn'], borderwidth=0, focusthickness=0,
                        padding=(px(12), px(9)), relief='flat', anchor='center')
        style.map('Primary.TButton',
                  background=[('disabled', '#b9c3ce'), ('pressed', ACCENT_DARK),
                              ('active', ACCENT_DARK)],
                  foreground=[('disabled', '#f0f3f6')])

        style.configure('Ghost.TButton', background=CARD, foreground=INK,
                        font=self.fonts['ui'], borderwidth=1, bordercolor=RULE,
                        focusthickness=0, padding=(px(12), px(7)), relief='flat')
        style.map('Ghost.TButton',
                  background=[('pressed', '#e7ebf0'), ('active', '#f4f6f9')],
                  bordercolor=[('active', ACCENT)])

        style.configure('Stop.TButton', background=CARD, foreground=ERROR,
                        font=self.fonts['btn'], borderwidth=1, bordercolor=RULE,
                        focusthickness=0, padding=(px(12), px(9)), relief='flat')
        style.map('Stop.TButton',
                  background=[('pressed', '#f6e6e4'), ('active', '#fbf1f0'),
                              ('disabled', PAPER)],
                  foreground=[('disabled', '#b9c3ce')],
                  bordercolor=[('active', ERROR)])

        for name in ('TCombobox', 'TSpinbox', 'TEntry'):
            style.configure(name, fieldbackground=CARD, background=CARD,
                            foreground=INK, bordercolor=RULE, lightcolor=CARD,
                            darkcolor=CARD, arrowcolor=MUTED, insertcolor=INK,
                            relief='flat', padding=px(4), font=self.fonts['ui'])
            style.map(name,
                      bordercolor=[('focus', ACCENT), ('hover', '#c2cad4')],
                      arrowcolor=[('disabled', '#c2cad4')],
                      fieldbackground=[('disabled', PAPER), ('readonly', CARD)],
                      foreground=[('disabled', '#a7b0bb')])

        # readonly Combobox のドロップダウン配色
        self.root.option_add('*TCombobox*Listbox.background', CARD)
        self.root.option_add('*TCombobox*Listbox.foreground', INK)
        self.root.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
        self.root.option_add('*TCombobox*Listbox.font', self.fonts['ui'])

    # ---------------------------------------------------------------------- UI
    def _step(self, parent: tk.Widget, number: str, text: str) -> None:
        """「1 キャプチャ範囲」の見出し。範囲→ページ送り→出力は実際に順序を持つ工程。"""
        px = self.px
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=(0, px(4)))
        ttk.Label(row, text=f'{number}   {text}', style='Step.TLabel').pack(side='left')
        tk.Frame(row, bg=RULE, height=1).pack(
            side='left', fill='x', expand=True, padx=(px(10), 0), pady=(px(7), 0))

    def _build_ui(self) -> None:
        px = self.px
        self.inputs: list[tk.Widget] = []   # 実行中に無効化する入力ウィジェット

        outer = ttk.Frame(self.root, padding=(px(20), px(12), px(20), px(10)))
        outer.pack(fill='both', expand=True)

        # --- ヘッダー -------------------------------------------------------
        tk.Label(outer, text=APP_TITLE, bg=PAPER, fg=INK, font=self.fonts['title'],
                 anchor='w').pack(fill='x')
        tk.Label(outer, text='範囲を選んで開始。矢印キーを送りながら全ページを取り込みます。',
                 bg=PAPER, fg=MUTED, font=self.fonts['ui_sm'], anchor='w'
                 ).pack(fill='x', pady=(px(1), px(10)))

        # --- 1 範囲 ---------------------------------------------------------
        self._step(outer, '1', 'キャプチャ範囲')

        self.readout = Readout(outer, px, self.fonts)
        self.readout.pack(fill='x')

        # 範囲を選ぶ / 画面全体。縦を増やさないよう 1 行に並べる。
        pick = ttk.Frame(outer)
        pick.pack(fill='x', pady=(px(8), px(10)))
        pick.columnconfigure(0, weight=2, uniform='r')
        pick.columnconfigure(1, weight=1, uniform='r')

        self.region_btn = ttk.Button(pick, text='キャプチャ範囲を選択', width=1,
                                     style='Ghost.TButton',
                                     command=self.on_select_region)
        self.region_btn.grid(row=0, column=0, sticky='ew')
        self.fullscreen_btn = ttk.Button(pick, text='画面全体', width=1,
                                         style='Ghost.TButton',
                                         command=self.on_select_fullscreen)
        self.fullscreen_btn.grid(row=0, column=1, sticky='ew', padx=(px(8), 0))
        Tooltip(self.fullscreen_btn, 'ドラッグせずに画面全体を範囲にします。'
                                     'ビューアーは最大化しておくと、このアプリの'
                                     'ウィンドウが写り込みません。',
                self.fonts['ui_sm'], px(280))

        # --- 2 ページ送り ---------------------------------------------------
        self._step(outer, '2', 'ページ送り')

        grid = ttk.Frame(outer)
        grid.pack(fill='x')
        grid.columnconfigure(0, weight=1, uniform='p')
        grid.columnconfigure(1, weight=1, uniform='p')

        self.direction = tk.StringVar(value='右 (→)')
        self._field(grid, 0, 0, 'ページ送りキー', colspan=2, widget='combo',
                    var=self.direction, values=list(DIRECTION_KEYS.keys()),
                    tip='1 ページごとに送るキーです。「なし」を選ぶと自分でめくる間、'
                        '一定間隔で撮り続けます（重複検知は無効になります）。')

        self.page_delay = tk.StringVar(value=str(DEFAULT_PAGE_DELAY))
        self._field(grid, 1, 0, '最短待機', unit='ms', widget='spin',
                    var=self.page_delay, from_=0, to=10000, increment=100,
                    tip='キーを送ってから撮るまでの最低待ち時間です。実際にはページが'
                        '変わるまで自動で待ち、変わらなければキーを送り直すので、'
                        '通常は既定のままで大丈夫です。'
                        '（「なし」を選んだ手動モードでは撮影間隔になります）')

        self.max_pages = tk.StringVar(value=str(DEFAULT_MAX_PAGES))
        self._field(grid, 1, 1, '最大ページ数', unit='ページ', widget='spin',
                    var=self.max_pages, from_=1, to=9999, increment=10,
                    tip='暴走防止の安全上限です。ここに達すると自動で止まります。')

        self.dup_threshold = tk.StringVar(value=str(DEFAULT_DUP_THRESHOLD))
        self._field(grid, 2, 0, '重複検知しきい値', widget='spin',
                    var=self.dup_threshold, from_=0, to=255, increment=1,
                    tip='ページが変わったかどうかの感度です。大きいほど変化を拾いにくく'
                        'なり、止まりやすくなります。ページが飛ぶときは小さく、最終ページで'
                        '止まらないときは大きくしてください。既定は 3。')

        self.start_delay = tk.StringVar(value=str(DEFAULT_START_DELAY))
        self._field(grid, 2, 1, '開始前の待機', unit='秒', widget='spin',
                    var=self.start_delay, from_=0, to=60, increment=1,
                    tip='開始を押してから撮り始めるまでの猶予です。この間に取り込みたい'
                        'ビューアーをクリックして前面にしてください。')

        # --- 3 出力 ---------------------------------------------------------
        tk.Frame(outer, bg=PAPER, height=px(4)).pack()
        self._step(outer, '3', '出力')

        out = ttk.Frame(outer)
        out.pack(fill='x')
        out.columnconfigure(0, weight=1, uniform='o')
        out.columnconfigure(1, weight=1, uniform='o')

        self.output_mode = tk.StringVar(value=DEFAULT_OUTPUT_MODE)
        self._field(out, 0, 0, '出力形式', widget='combo',
                    var=self.output_mode, values=list(OUTPUT_MODES.keys()),
                    tip='結合 PDF は閲覧・共有向き、ページごとの PNG は資料への'
                        '貼り付けや編集向きです。迷ったら両方のままで大丈夫です。')

        self.quality = tk.StringVar(value=QUALITY_HIGH)
        self._field(out, 0, 1, 'PDF品質', widget='combo',
                    var=self.quality, values=QUALITY_CHOICES,
                    tip='高画質 = PNG を無劣化のまま結合。標準 / 軽量 は縮小して JPEG 化し、'
                        'ファイルサイズを抑えます。')

        head = ttk.Frame(out)
        head.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, px(2)))
        ttk.Label(head, text='保存先フォルダ', style='Field.TLabel').pack(side='left')
        ttk.Label(head, text='この中にフォルダを作って保存します',
                  style='Unit.TLabel').pack(side='right')

        path_row = ttk.Frame(out)
        path_row.grid(row=2, column=0, columnspan=2, sticky='ew')
        path_row.columnconfigure(0, weight=1)

        self.output_dir = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.output_entry = ttk.Entry(path_row, textvariable=self.output_dir,
                                      width=12, font=self.fonts['mono_sm'])
        self.output_entry.grid(row=0, column=0, sticky='ew')
        self.browse_btn = ttk.Button(path_row, text='参照', style='Ghost.TButton',
                                     width=5, command=self.on_browse)
        self.browse_btn.grid(row=0, column=1, padx=(px(8), 0))

        tk.Frame(out, bg=PAPER, height=px(8)).grid(row=3, column=0)

        self.folder_name = tk.StringVar(value='')
        self._field(out, 4, 0, 'フォルダ名', colspan=2, widget='entry',
                    var=self.folder_name, unit='空欄なら capture_日時',
                    tip='保存先フォルダの中に作るフォルダの名前です。本のタイトルなどを'
                        '入れておくと、あとで探しやすくなります。空欄のままなら '
                        'capture_日時 になります。同じ名前のフォルダが既にあるときは'
                        '末尾に _2, _3 … を付けるので、上書きされることはありません。')

        # --- アクション（下端に固定） ----------------------------------------
        actions = ttk.Frame(outer)
        actions.pack(fill='x', side='bottom')

        self.status_label = tk.Label(
            actions, text='準備完了', bg=PAPER, fg=ACCENT, font=self.fonts['ui_sm'],
            anchor='w', justify='left', wraplength=px(430),
        )
        self.status_label.pack(fill='x', side='bottom', pady=(px(7), 0))

        buttons = ttk.Frame(actions)
        buttons.pack(fill='x', side='bottom')
        buttons.columnconfigure(0, weight=3, uniform='b')
        buttons.columnconfigure(1, weight=2, uniform='b')

        # width=1 + sticky='ew': 列の重み(3:2)どおりに主/副の幅を決める。
        # ラベル長で列幅が決まってしまうと、停止ボタンの方が太くなり主従が逆転する。
        self.start_btn = ttk.Button(buttons, text='キャプチャ開始', width=1,
                                    style='Primary.TButton', command=self.on_start)
        self.start_btn.grid(row=0, column=0, sticky='ew')
        self.stop_btn = ttk.Button(buttons, text='停止（Escキーでも可）', width=1,
                                   style='Stop.TButton', state='disabled',
                                   command=self.on_stop)
        self.stop_btn.grid(row=0, column=1, sticky='ew', padx=(px(8), 0))

        self.inputs.extend([self.output_entry, self.browse_btn,
                            self.region_btn, self.fullscreen_btn])

    def _field(self, parent, row, col, label, *, widget, var, colspan=1,
               unit=None, values=None, from_=0, to=100, increment=1, tip=None):
        """ラベル + 入力欄を 1 セルに置く。"""
        px = self.px
        cell = ttk.Frame(parent)
        cell.grid(row=row, column=col, columnspan=colspan, sticky='ew',
                  padx=(0, px(8) if (colspan == 1 and col == 0) else 0),
                  pady=(0, px(5)))
        cell.columnconfigure(0, weight=1)

        head = ttk.Frame(cell)
        head.grid(row=0, column=0, sticky='ew', pady=(0, px(2)))
        ttk.Label(head, text=label, style='Field.TLabel').pack(side='left')
        if unit:
            ttk.Label(head, text=unit, style='Unit.TLabel').pack(side='right')

        if widget == 'combo':
            w = ttk.Combobox(cell, textvariable=var, values=values, width=10,
                             state='readonly', font=self.fonts['ui'])
        elif widget == 'entry':
            w = ttk.Entry(cell, textvariable=var, width=12,
                          font=self.fonts['mono_sm'])
        else:
            w = ttk.Spinbox(cell, textvariable=var, from_=from_, to=to, width=6,
                            increment=increment, font=self.fonts['mono'],
                            justify='right')
        w.grid(row=1, column=0, sticky='ew')

        if tip:
            tooltip_args = (self.fonts['ui_sm'], px(280))
            Tooltip(w, tip, *tooltip_args)
            Tooltip(head, tip, *tooltip_args)

        self.inputs.append(w)
        return w

    # ------------------------------------------------------------------ status
    def _set_status(self, text: str, kind: str = 'info') -> None:
        colors = {'info': ACCENT, 'ok': OK, 'error': ERROR, 'muted': MUTED}
        self.status_label.configure(text=text, fg=colors.get(kind, ACCENT))

    # ---------------------------------------------------------------- handlers
    def on_select_region(self) -> None:
        self.root.withdraw()
        self.root.update()
        try:
            region = RegionSelector(self.root).select()
        finally:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

        if region is None:
            self._set_status('範囲の選択をキャンセルしました', 'muted')
            return

        self._apply_region(region)

    def on_select_fullscreen(self) -> None:
        self._apply_region(primary_monitor_region())

    def _apply_region(self, region: dict) -> None:
        self.region = region
        self.readout.set_region(region)
        self._set_status('範囲を選択しました。ページ送りと出力を確認して開始してください。',
                         'info')

    def on_browse(self) -> None:
        current = self.output_dir.get().strip()
        path = filedialog.askdirectory(
            title='保存先フォルダ',
            initialdir=current if os.path.isdir(current) else os.path.expanduser('~'),
        )
        if path:
            self.output_dir.set(os.path.normpath(path))

    def _collect_config(self) -> dict | None:
        if self.region is None:
            messagebox.showwarning(APP_TITLE, 'まずキャプチャ範囲を選択してください')
            return None
        try:
            config = {
                'region': self.region,
                'direction': self.direction.get(),
                'page_delay': int(self.page_delay.get()),
                'max_pages': int(self.max_pages.get()),
                'dup_threshold': float(self.dup_threshold.get()),
                'start_delay': int(self.start_delay.get()),
                'quality': self.quality.get(),
                'output_mode': self.output_mode.get(),
                'output_base': self.output_dir.get().strip(),
                'output_name': self.folder_name.get().strip(),
            }
        except (ValueError, TypeError):
            messagebox.showerror(APP_TITLE, '数値の項目を確認してください')
            return None

        base = config['output_base']
        if not base:
            messagebox.showerror(APP_TITLE, '保存先フォルダを指定してください')
            return None
        if not os.path.isdir(base):
            messagebox.showerror(APP_TITLE,
                                 f'保存先フォルダが見つかりません:\n{base}')
            return None

        # フォルダ名は空欄なら capture_日時。入力があるときだけ、作れる名前か見る。
        # （エンジン側でも正規化するが、撮り終えてから弾かれると撮り直しになる）
        name = config['output_name']
        if name:
            invalid = sorted(set(name) & set(INVALID_NAME_CHARS))
            if invalid:
                messagebox.showerror(
                    APP_TITLE,
                    'フォルダ名に使えない文字が含まれています:\n'
                    + '  '.join(invalid))
                return None
            if not sanitize_folder_name(name):
                messagebox.showerror(APP_TITLE, 'フォルダ名を確認してください')
                return None

        # 保存は base の中に毎回新しいフォルダを作って行い、同名があれば _2, _3 …
        # と足すため、既存ファイルの上書きは起こらない（上書き確認は不要）
        return config

    def on_start(self) -> None:
        config = self._collect_config()
        if config is None:
            return

        self._set_running(True)
        self.readout.set_progress(0, config['max_pages'])

        self.engine = CaptureEngine(
            config,
            on_status=lambda text: self.root.after(0, self._on_status, text),
            on_done=lambda path: self.root.after(0, self._on_done, path),
            on_progress=lambda page, total: self.root.after(
                0, self.readout.set_progress, page, total),
        )
        threading.Thread(target=self.engine.run, daemon=True).start()

    def on_stop(self) -> None:
        if self.engine is not None:
            self.engine.stop()
            self._set_status('停止しています…', 'muted')

    # ------------------------------------------- コールバック（メインスレッド）
    def _on_status(self, text: str) -> None:
        kind = 'info'
        if text.startswith('完成:'):
            kind = 'ok'
        elif text.startswith(('PDF作成に失敗', '取得ページがありません')):
            kind = 'error'
        elif text.startswith('中断しました'):
            kind = 'muted'
        self._set_status(text, kind)

    def _on_done(self, _out_dir: str | None) -> None:
        self._set_running(False)
        # キャプチャ中は取り込み先のビューアーが前面にある。こちらを前に出さないと、
        # 撮影が止まったあと何も起きていないように見える（完了表示がビューアーの
        # 後ろに隠れる）。前面に戻して「完成: 保存先」のステータスを見せる。
        # 何冊も続けて取り込めるよう、確認ダイアログもエクスプローラーも出さない。
        self._raise_window()
        self.engine = None

    def _raise_window(self) -> None:
        """自ウィンドウを前面に戻す。

        Windows は非アクティブなプロセスが前面を奪うのを拒むため、lift() だけでは
        ビューアーの後ろに隠れたままになることがある。topmost を一瞬だけ立てて
        すぐ下ろすと、最前面に居座らせずに前面へ出せる。
        """
        self.root.deiconify()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(200, self._clear_topmost)
        try:
            self.root.focus_force()
        except tk.TclError:
            pass

    def _clear_topmost(self) -> None:
        try:
            self.root.attributes('-topmost', False)
        except tk.TclError:
            pass   # 既に閉じられている

    def _set_running(self, running: bool) -> None:
        self.running = running
        state = 'disabled' if running else 'normal'
        self.start_btn.configure(state=state)
        self.stop_btn.configure(state='normal' if running else 'disabled')
        for widget in self.inputs:
            if isinstance(widget, ttk.Combobox):
                widget.configure(state='disabled' if running else 'readonly')
            else:
                widget.configure(state=state)
        if not running:
            self.readout.set_progress(None, None)

    def _on_close(self) -> None:
        if self.running and self.engine is not None:
            self.engine.stop()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
