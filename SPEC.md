# 仕様書: 画面連続キャプチャ → PDF 変換ツール

- バージョン: 1.0
- 対象読者: 実装エージェント（Claude Code）
- 本書のみで実装可能な自己完結仕様とする。曖昧な点は本書の既定値を正とする。

---

## 1. 概要

デスクトップ画面の指定範囲を連続スクリーンショットし、矢印キーを送信して対象アプリのページを自動でめくりながら全ページを取得、最後に画像群を 1 つの PDF に結合する Windows 向けデスクトップツール。

- 想定対象: 矢印キーでページ送りできるビューアー全般（PDF ビューアー、PowerPoint、電子書籍リーダー等）
- 想定用途: 自分の資料・スライド・私的利用が認められたコンテンツの PDF 化
- 完全ローカル動作。ネットワーク通信・テレメトリ・外部送信は一切行わない
- 透かし・ロゴ・課金導線・機能制限は一切実装しない

## 2. 動作環境・技術スタック

| 項目 | 内容 |
|---|---|
| OS | Windows 10 / 11 (64bit) |
| ランタイム | Python 3.9 以上（3.11 推奨） |
| GUI | tkinter（標準ライブラリ） |
| スクリーンショット | mss >= 9.0.1 |
| 画像処理 | Pillow >= 10.0.0 |
| キー送信 / Esc 監視 | pynput >= 1.7.6 |
| PDF 結合 | img2pdf >= 0.5.1 |

`requirements.txt` に上記 4 パッケージを記載すること。

## 3. 非目標（Non-goals）

- DRM の解除、保護されたコンテンツへのアクセス支援は行わない（README に私的利用・対象アプリの規約遵守の注意書きを記載する）
- macOS / Linux 対応
- OCR・AI 機能（Phase 2 候補、§13 参照）
- インストーラー / exe 化（Phase 2 候補）

## 4. プロジェクト構成

```
project/
├── main.py              # エントリポイント + GUI
├── region_selector.py   # キャプチャ範囲選択オーバーレイ
├── capture_engine.py    # キャプチャループ本体
├── pdf_builder.py       # 画像 → PDF 結合
├── requirements.txt
├── README.md            # セットアップ・使い方・注意事項
└── tests/
    └── test_core.py     # 純粋ロジックのユニットテスト
```

推奨実装順: ① pdf_builder + テスト → ② region_selector → ③ capture_engine + テスト → ④ main（GUI 統合）→ ⑤ README。

## 5. モジュール仕様

### 5.1 region_selector.py

公開 API:

```python
class RegionSelector:
    def __init__(self, root: tk.Tk): ...
    def select(self) -> dict | None
```

- 全画面 `Toplevel` を表示する。属性: `-fullscreen True`, `-alpha 0.25`（半透明で下の画面が見える）, `-topmost True`, カーソル `crosshair`
- 左ドラッグで矩形選択。ドラッグ中はシアン枠（`#00e5ff`, width=2）をリアルタイム描画する
- **座標は `event.x_root` / `event.y_root`（スクリーン物理ピクセル）を使用する**。描画用のキャンバス座標（`event.x`/`event.y`）と混同しないこと（§9.1 の DPI 設定が前提）
- 戻り値: `{'left': int, 'top': int, 'width': int, 'height': int}`（物理 px、mss にそのまま渡せる形式）
- 幅または高さが 5px 以下のドラッグは無効として選択を継続する
- Esc キーでキャンセル → `None` を返す
- `wait_window()` でモーダル動作にする

### 5.2 pdf_builder.py

公開 API:

```python
def build_pdf(image_paths: list[str], output_path: str, quality: str = '高画質') -> str
```

| quality | 処理 |
|---|---|
| `高画質` | PNG を img2pdf で無劣化結合（再エンコードなし） |
| `標準` | 各画像を 0.85 倍に縮小 → JPEG q=85 に変換して結合 |
| `軽量` | 各画像を 0.60 倍に縮小 → JPEG q=70 に変換して結合 |

- `output_path` が `.pdf` で終わらない場合は付与する
- 出力先ディレクトリは `os.makedirs(..., exist_ok=True)` で作成する
- 標準/軽量で生成した一時 JPEG は `try/finally` で必ず削除する
- 戻り値は実際に書き出したパス

### 5.3 capture_engine.py

公開 API:

```python
DIRECTION_KEYS = {
    '右 (→)': Key.right,
    '左 (←)': Key.left,
    '下 (↓)': Key.down,
    'なし（手動でめくる）': None,
}

class CaptureEngine:
    def __init__(self, config: dict, on_status: Callable[[str], None],
                 on_done: Callable[[str | None], None]): ...
    def run(self) -> None   # ワーカースレッドで実行される
    def stop(self) -> None  # threading.Event で中断要求
```

`config` のキー:

| キー | 型 | 意味 |
|---|---|---|
| `region` | dict | 範囲選択の戻り値 |
| `direction` | str | DIRECTION_KEYS のキー |
| `page_delay` | int | ページ送り後の待機 (ms) |
| `max_pages` | int | 取得ページ数の安全上限 |
| `dup_threshold` | float | 重複検知しきい値 |
| `start_delay` | int | 開始前カウントダウン (秒) |
| `quality` | str | PDF 品質 |
| `output_path` | str | 保存先 |

処理フロー（`run()`）:

```
1. pynput の keyboard.Listener を起動し、Esc 押下で stop イベントを立てる
2. start_delay 秒カウントダウン。毎秒 on_status で
   「N 秒後に開始… 取り込みたいビューアーを前面にしてください」を通知
3. tempfile.mkdtemp(prefix='...') に作業ディレクトリを作成
4. ループ（page = 1..max_pages）:
   a. stop が立っていれば「中断しました」を通知して break
   b. mss で region をキャプチャし PIL Image に変換
   c. 指紋 sig を計算
   d. direction が None でなく、かつ前ページ指紋との diff < dup_threshold なら
      「同じページを検知 → 末尾と判断して停止」を通知して break
      （このページは保存しない）
   e. page_{page:04d}.png として保存、on_status で「N ページ目を取得」
   f. direction が None でなければ該当キーを press/release で 1 回送信
   g. page_delay ミリ秒 sleep
5. Listener を finally で停止
6. 保存 0 枚なら「取得ページがありません」を通知し on_done(None) で終了
7. build_pdf を呼び、成功なら「完成: <path>」+ on_done(path)、
   例外時は「PDF作成に失敗: <e>」+ on_done(None)
```

画像変換・指紋・差分の実装（この通りに実装すること）:

```python
# mss の生データは BGRA。以下で RGB 化する
raw = sct.grab(region)
img = Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX')

# 指紋: 32x32 グレースケールのバイト列
# 注意: Image.getdata() は Pillow で非推奨のため tobytes() を使う
sig = list(img.convert('L').resize((32, 32)).tobytes())

# 差分: 平均絶対差（0=完全一致）。どちらかが None なら 255.0 を返す
diff = sum(abs(p - q) for p, q in zip(a, b)) / len(a)
```

重複検知の設計根拠（検証済み実測値）: 同一画面同士の diff = 0.0、内容の異なるページ同士は 100 前後以上になる。実画面ではレンダリング揺らぎがあるため既定しきい値は 3 とする。

### 5.4 main.py

- エントリポイント。`python main.py` で起動
- **tkinter 初期化より前に** DPI 設定を行う（§9.1）
- ウィンドウ: タイトル「画面キャプチャ → PDF」、サイズ 470x600、リサイズ不可
- コントロール（上から順）:
  1. 範囲ラベル（初期値「範囲: 未選択」。選択後は `範囲: {w}×{h} @ ({left},{top})`）
  2. ボタン「キャプチャ範囲を選択」
  3. Combobox「ページ送りキー」（DIRECTION_KEYS のキー、readonly、既定 `右 (→)`）
  4. 数値入力 4 項目（§6 の既定値）
  5. Combobox「PDF品質」（高画質/標準/軽量、readonly、既定 高画質）
  6. 保存先 Entry + 参照ボタン（`filedialog.asksaveasfilename`、既定 `~/Desktop/capture.pdf`）
  7. ボタン「キャプチャ開始」/ ボタン「停止（Escキーでも可）」
  8. ステータスラベル（文字色 `#0066cc`、`wraplength=430`、初期値「準備完了」）
- 範囲選択中はメインウィンドウを `withdraw()` し、終了後 `deiconify()` する
- 開始時のバリデーション: 範囲未選択なら警告ダイアログ、数値パース失敗ならエラーダイアログを出し、開始しない
- キャプチャ実行中は開始ボタンを `disabled`、完了（on_done）で `normal` に戻す
- 完了時に出力パスがあれば `messagebox.showinfo` で通知する

## 6. パラメータ既定値

| 項目 | 既定値 | 備考 |
|---|---|---|
| ページ送り待機 (ms) | 700 | 重いビューアーでは 1000〜1500 を README で案内 |
| 最大ページ数 | 500 | 暴走防止の安全上限 |
| 重複検知しきい値 | 3 | 大きいほど「同じ」と判定されやすい（=止まりやすい） |
| 開始前の待機 (秒) | 4 | 対象ウィンドウを前面にする猶予 |
| PDF品質 | 高画質 | |
| 保存先 | `~/Desktop/capture.pdf` | |

## 7. 機能要件

| ID | 要件 |
|---|---|
| F-01 | ドラッグによる範囲選択（半透明オーバーレイ、Esc キャンセル） |
| F-02 | 開始前カウントダウンとステータス通知 |
| F-03 | 指定範囲の連続キャプチャ（PNG、連番 4 桁） |
| F-04 | 矢印キー送信による自動ページ送り（右/左/下/なし） |
| F-05 | 重複ページ検知による末尾自動停止（自動送りのときのみ有効） |
| F-06 | 最大ページ数による安全停止 |
| F-07 | Esc キー（グローバル）および停止ボタンによる即時中断 |
| F-08 | 品質 3 段階での PDF 生成と完了ダイアログ |
| F-09 | 進行状況のステータス表示（UI スレッド経由） |
| F-10 | 保存先のファイルダイアログ指定 |

## 8. エラー処理

- 範囲未選択で開始 → 警告ダイアログ「まずキャプチャ範囲を選択してください」
- 数値項目のパース失敗 → エラーダイアログ「数値の項目を確認してください」
- 取得 0 ページで終了 → ステータス通知のみ（ダイアログなし）、`on_done(None)`
- PDF 生成で例外 → ステータスにエラー内容を表示、`on_done(None)`。アプリはクラッシュさせない

## 9. 実装上の必須事項（ハマりどころ）

### 9.1 高 DPI 対応

Windows の表示スケール（125% / 150% 等）で座標がずれるのを防ぐため、**tkinter を初期化する前に**以下を実行する:

```python
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
except Exception:
    pass  # 古い環境では失敗してもよい
```

これにより tkinter のスクリーン座標（`x_root`/`y_root`）と mss の物理ピクセルが一致する。

### 9.2 スレッド境界

- `CaptureEngine.run()` は `threading.Thread(daemon=True)` で実行する
- **tkinter ウィジェットはメインスレッド以外から絶対に触らない**。`on_status` / `on_done` は `root.after(0, ...)` でメインスレッドに委譲して UI を更新する

### 9.3 キー送信の宛先

pynput のキー送信は「その時点でアクティブなウィンドウ」に届く。カウントダウン中に対象ビューアーをクリックして前面にする運用を README に明記する。

### 9.4 その他

- Pillow の `Image.getdata()` は非推奨 → `tobytes()` を使用（§5.3）
- 一時ファイル（作業用 PNG / 品質変換用 JPEG）は処理終了時に残さない

## 10. 受け入れ基準

| ID | 基準 |
|---|---|
| AC-01 | 表示スケール 150% の環境で、選択した範囲と実際のキャプチャ範囲が一致する |
| AC-02 | ページ送り「右 (→)」で PDF ビューアー等の複数ページを自動取得し、最終ページで自動停止する |
| AC-03 | ページ送り「左 (←)」「下 (↓)」でも同様に動作する |
| AC-04 | 「なし（手動でめくる）」では重複検知が無効で、Esc または最大ページ数で終了する |
| AC-05 | キャプチャ中に Esc を押すと 1 秒以内にループが止まり、それまでのページで PDF が生成される |
| AC-06 | 品質 3 種でそれぞれ PDF が生成でき、軽量 < 標準 < 高画質 の順にファイルサイズが小さくなる（同一入力・写真的な画像の場合） |
| AC-07 | 実行終了後、一時ディレクトリ外に中間ファイルが残らない |
| AC-08 | 範囲未選択・数値不正の状態で開始してもクラッシュせず、ダイアログで案内される |
| AC-09 | 出力に透かし・ロゴ等が一切含まれない（自作のため対象概念そのものが存在しないこと） |

## 11. テスト

自動テスト（`tests/test_core.py`、pytest。GUI・実画面キャプチャは対象外）:

1. `build_pdf`: ダミー PNG 3 枚から 3 品質すべてで PDF が生成される／一時 JPEG が残らない／`.pdf` 拡張子が自動付与される
2. 指紋・差分: 同一画像同士の diff が 0.0、単色の異なる 2 画像の diff が 50 以上になる
3. `DIRECTION_KEYS`: 「なし」が None にマップされる

手動テスト: README に手順を記載（対象アプリを開く → 範囲選択 → 開始 → 前面化 → 自動停止確認 → PDF を開いて確認）。

## 12. README に含める内容

セットアップ手順（venv 作成 → `pip install -r requirements.txt` → `python main.py`）、使い方、パラメータの目安（§6 の表）、キー送信がアクティブウィンドウ宛てである注意、私的利用の範囲および取り込み対象アプリの利用規約・関連法令を守る旨の注意書き。

## 13. Phase 2 候補（今回のスコープ外・実装しない）

- 出力形式の選択（PDF のみ / 画像フォルダのみ / 両方）
- 複数 PDF の結合ツール
- 設定値の JSON 永続化（前回値の復元）
- PyInstaller による単一 exe 化
- Anthropic API を使った保存名・概要メモの自動提案
