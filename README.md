# 画面キャプチャ → PDF

デスクトップ画面の指定した範囲を連続スクリーンショットし、矢印キーで対象アプリのページを自動でめくりながら全ページを取得、最後に 1 つの PDF に結合する Windows 向けツールです。

- 対象: 矢印キーでページ送りできるビューアー全般（PDF ビューアー、PowerPoint、電子書籍リーダー等）
- **完全ローカル動作**。ネットワーク通信・テレメトリ・外部送信は一切ありません
- 透かし・ロゴ・課金・機能制限なし

**アプリの使い方は [MANUAL.md](MANUAL.md) を参照してください。** この README はリポジトリを触る人向けに、exe の作り方と開発手順をまとめたものです。

## 動作環境

| 項目 | 内容 |
|---|---|
| OS | Windows 10 / 11（64bit） |
| Python | exe を使うだけなら不要。ビルド・ソース実行には 3.9 以上（3.11 推奨） |

## exe を作る

```powershell
# 1. このリポジトリを取得して移動
git clone <このリポジトリのURL>
cd BookToPDF

# 2. 仮想環境を作成して有効化
python -m venv .venv
.venv\Scripts\activate

# 3. 依存パッケージをインストール
pip install -r requirements.txt

# 4. ビルド
python build.py
```

`python build.py` だけで `dist\` に配布物 2 つが生成されます。PyInstaller が未インストールなら自動で入るので、事前準備は不要です。

| 生成物 | 内容 |
|---|---|
| `dist\BookToPDF.exe` | Python 不要の単体実行ファイル（約 22 MB、コンソール非表示） |
| `dist\使い方.pdf` | 利用者向けマニュアル（A4 / 2 ページ）。`MANUAL.md` から自動生成 |

**この 2 ファイルをセットで配布します。** exe を受け取った人は Python を入れる必要がなく、使い方は同梱の PDF を読めば分かる、という状態になります。

### コマンドの使い分け

| やりたいこと | コマンド | 結果 |
|---|---|---|
| exe を作る | `python build.py` | `dist\` に exe と 使い方.pdf が生成される |
| アプリを動かす（開発中の確認用） | `python main.py` | GUI が起動する。**exe は作られません** |

### ビルドに関する補足

- 使い方 PDF は `MANUAL.md` を組版したものです。使い方を書き換えたら `python build.py` を流し直せば、exe と PDF の内容が必ず揃います
- 組版は Pillow で A4 ページを描画し、本アプリ自身の `pdf_builder.build_pdf`（img2pdf）で結合しています。新たな依存パッケージは増えません。日本語フォントは Windows 標準の游ゴシック / メイリオ / MS ゴシックを使うため、PDF 生成は Windows 上でのみ動きます
- exe の初回起動には数秒かかります。単一ファイル形式のため、起動時に一時フォルダへ展開するからです。速くしたい場合は `BookToPDF.spec` の `EXE(...)` を `COLLECT` 形式（フォルダ配布）に変更してください
- pynput でキー送信を行う都合上、セキュリティソフトが未署名の exe を警告することがあります。配布するならコード署名を検討してください
- `build\` は PyInstaller の中間ファイル置き場で、成果物ではありません。消して構いません（`dist\` が配布物です）

## ソースから動かす

exe を作らずに直接動かす場合は、上の手順 3 まで済ませたうえで:

```powershell
python main.py
```

2 回目以降は `.venv\Scripts\activate` → `python main.py` だけで起動できます。

## テスト

```powershell
# ユニットテスト（GUI・実画面キャプチャは対象外の純粋ロジックのみ）
python -m pytest tests -v
```

実画面のキャプチャと GUI は自動テストの対象外なので、次の手順で手動確認します。

1. 複数ページの PDF などをビューアーで開く
2. 本アプリで表示部分を範囲選択 → 「キャプチャ開始」
3. カウントダウン中にビューアーをクリックして前面化
4. 最終ページで自動停止することを確認
5. 保存された PDF を開き、全ページが順番どおり入っていることを確認

## プロジェクト構成

```
├── main.py              # エントリポイント + GUI
├── region_selector.py   # キャプチャ範囲選択オーバーレイ
├── capture_engine.py    # キャプチャループ本体
├── pdf_builder.py       # 画像 → PDF 結合
├── build.py             # 配布物の一括ビルド（exe + 使い方 PDF）
├── manual_pdf.py        # MANUAL.md → 使い方 PDF の組版
├── BookToPDF.spec       # PyInstaller 設定
├── MANUAL.md            # 利用者向けの使い方（PDF の生成元）
├── SPEC.md              # 実装仕様書
├── requirements.txt
└── tests/
    └── test_core.py     # 純粋ロジックのユニットテスト
```
