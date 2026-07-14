"""MANUAL.md（利用者向けの使い方）を A4 の PDF に組版する。

MANUAL.md を唯一の情報源とし、その全体をそのまま PDF にする。使い方を
Markdown と PDF で二重管理しないための仕組み。exe に添える 使い方.pdf は
build.py がこのモジュールを呼んで生成する。

組版は Pillow で A4 ページを画像として描画し、既存の pdf_builder.build_pdf
（img2pdf）で 1 つの PDF に結合する。アプリ本体と同じ依存だけで完結する。
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile

from PIL import Image, ImageDraw, ImageFont

from pdf_builder import QUALITY_HIGH, build_pdf

# --- ページ設定 ---------------------------------------------------------------
DPI = 150
PAGE_W, PAGE_H = 1240, 1754  # A4 縦 @150dpi (210mm x 297mm)
MARGIN_X = 105
MARGIN_TOP = 110
MARGIN_BOTTOM = 130
CONTENT_W = PAGE_W - MARGIN_X * 2
CONTENT_BOTTOM = PAGE_H - MARGIN_BOTTOM

# --- 色 -----------------------------------------------------------------------
INK = (26, 26, 26)
MUTED = (95, 95, 95)
RULE = (208, 208, 208)
ACCENT = (30, 90, 160)
CODE_BG = (245, 246, 248)
CODE_INK = (40, 44, 52)
TABLE_HEAD_BG = (237, 240, 244)

# --- 文字サイズ ---------------------------------------------------------------
SIZE_H1 = 32
SIZE_H2 = 23
SIZE_H3 = 18
SIZE_BODY = 15
SIZE_CODE = 13
SIZE_TABLE = 14
SIZE_FOOT = 11

LINE_RATIO = 1.75  # 和文は行間を広めに取ると読みやすい

# 行頭・行末に置けない文字（簡易禁則処理）
NO_LINE_START = '、。，．）」』】〕》〉！？ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮー・:;,.!?)]}〜'
NO_LINE_END = '（「『【〔《〈([{'

# 分割せず 1 単位として扱う文字（英単語・パス・数値を途中で折り返さない）
_WORD_CHARS = re.compile(r'[0-9A-Za-z_.\-/\\:%+#@]')


# --- フォント -----------------------------------------------------------------
_FONT_DIR = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
# 等幅の MS ゴシックはコードブロックの罫線素片（└ ├ ─）も和文も出せるので
# コード用に使う。Consolas では和文が豆腐になる。
_CANDIDATES = {
    'regular': ('YuGothR.ttc', 'YuGothM.ttc', 'meiryo.ttc', 'msgothic.ttc'),
    'bold': ('YuGothB.ttc', 'meiryob.ttc', 'msgothic.ttc'),
    'mono': ('msgothic.ttc', 'meiryo.ttc'),
}
_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]

    for name in _CANDIDATES[kind]:
        path = os.path.join(_FONT_DIR, name)
        if os.path.exists(path):
            font = ImageFont.truetype(path, size)
            break
    else:
        raise RuntimeError(
            f'日本語フォントが見つかりません（探索先: {_FONT_DIR}）。'
            f'候補: {", ".join(_CANDIDATES[kind])}')

    _font_cache[key] = font
    return font


def _fonts(size: int) -> dict[str, ImageFont.FreeTypeFont]:
    """インライン記法（通常 / 太字 / コード）3 種のフォント一式。"""
    return {
        'normal': _font('regular', size),
        'bold': _font('bold', size),
        'code': _font('mono', size - 1),
    }


# --- Markdown パース ----------------------------------------------------------
def _parse(md: str) -> list[dict]:
    """Markdown を描画用のブロック列に変換する。"""
    blocks: list[dict] = []
    para: list[str] = []
    in_code = False
    code: list[str] = []
    table: list[list[str]] = []

    def flush_para() -> None:
        if para:
            blocks.append({'type': 'para', 'text': ' '.join(para)})
            para.clear()

    def flush_table() -> None:
        if table:
            blocks.append({'type': 'table', 'rows': [r[:] for r in table]})
            table.clear()

    for raw in md.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        # コードブロックは中身をそのまま保持する（禁則も折り返しもしない）
        if stripped.startswith('```'):
            if in_code:
                blocks.append({'type': 'code', 'lines': code[:]})
                code.clear()
            else:
                flush_para()
                flush_table()
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue

        # 見出し
        m = re.match(r'^(#{1,3})\s+(.*)$', stripped)
        if m:
            flush_para()
            flush_table()
            blocks.append({'type': f'h{len(m.group(1))}', 'text': m.group(2)})
            continue

        # 表（| a | b | 形式。|---|---| の区切り行は捨てる）
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            if all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
                continue
            flush_para()
            table.append(cells)
            continue
        flush_table()

        if not stripped:
            flush_para()
            continue

        # 引用
        if stripped.startswith('> '):
            flush_para()
            blocks.append({'type': 'quote', 'text': stripped[2:]})
            continue

        # 箇条書き / 番号付き（先頭の空白でネストを判定）
        indent = (len(line) - len(line.lstrip(' '))) // 2
        m = re.match(r'^[-*]\s+(.*)$', stripped)
        if m:
            flush_para()
            blocks.append({'type': 'li', 'text': m.group(1),
                           'marker': '・', 'indent': indent})
            continue
        m = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if m:
            flush_para()
            blocks.append({'type': 'li', 'text': m.group(2),
                           'marker': f'{m.group(1)}.', 'indent': indent})
            continue

        para.append(stripped)

    flush_para()
    flush_table()
    return blocks


_INLINE = re.compile(r'(\*\*.+?\*\*|`[^`]+`)')


def _runs(text: str) -> list[tuple[str, str]]:
    """インライン記法を (文字列, スタイル) の並びに分解する。"""
    out: list[tuple[str, str]] = []
    for part in _INLINE.split(text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            # 太字の中の `code` は入れ子解析せず、記号だけ落として太字で出す
            out.append((part[2:-2].replace('`', ''), 'bold'))
        elif part.startswith('`') and part.endswith('`'):
            out.append((part[1:-1], 'code'))
        else:
            out.append((part, 'normal'))
    return out


def _units(text: str) -> list[str]:
    """折り返しの最小単位。英数字の連なりは 1 単位にまとめて途中で切らない。"""
    units: list[str] = []
    buf = ''
    for ch in text:
        if _WORD_CHARS.match(ch):
            buf += ch
        else:
            if buf:
                units.append(buf)
                buf = ''
            units.append(ch)
    if buf:
        units.append(buf)
    return units


Line = list[tuple[str, str]]  # 1 行 = (文字列, スタイル) の並び


def _wrap(draw: ImageDraw.ImageDraw, runs: list[tuple[str, str]],
          fonts: dict, max_w: float) -> list[Line]:
    """スタイル付きテキストを max_w で折り返す（簡易禁則つき）。"""
    lines: list[Line] = []
    cur: Line = []
    cur_w = 0.0

    def push(unit: str, style: str, w: float) -> None:
        nonlocal cur_w
        if cur and cur[-1][1] == style:
            cur[-1] = (cur[-1][0] + unit, style)
        else:
            cur.append((unit, style))
        cur_w += w

    for text, style in runs:
        font = fonts[style]
        for unit in _units(text):
            w = draw.textlength(unit, font=font)
            if cur and cur_w + w > max_w and unit[0] not in NO_LINE_START:
                # 行末に置けない文字が末尾なら、それごと次行へ送る
                if cur[-1][0] and cur[-1][0][-1] in NO_LINE_END:
                    moved = cur[-1]
                    cur[-1] = (moved[0][:-1], moved[1])
                    lines.append([c for c in cur if c[0]])
                    cur = [(moved[0][-1], moved[1])]
                    cur_w = draw.textlength(moved[0][-1], font=fonts[moved[1]])
                else:
                    lines.append(cur)
                    cur = []
                    cur_w = 0.0
            push(unit, style, w)

    if cur:
        lines.append(cur)
    return lines or [[]]


def _draw_line(draw: ImageDraw.ImageDraw, x: float, y: float,
               line: Line, fonts: dict, color=INK) -> None:
    for text, style in line:
        font = fonts[style]
        fill = CODE_INK if style == 'code' else color
        draw.text((x, y), text, font=font, fill=fill)
        x += draw.textlength(text, font=font)


# --- 組版 ---------------------------------------------------------------------
class _Layout:
    """A4 ページを順に描画していく。ページ跨ぎは自動。"""

    def __init__(self, work_dir: str) -> None:
        self.work_dir = work_dir
        self.paths: list[str] = []
        self.page_no = 0
        self._new_page()

    def _new_page(self) -> None:
        self.page_no += 1
        self.img = Image.new('RGB', (PAGE_W, PAGE_H), 'white')
        self.draw = ImageDraw.Draw(self.img)
        self.y = MARGIN_TOP

    def _finish_page(self) -> None:
        foot = _font('regular', SIZE_FOOT)
        label = str(self.page_no)
        w = self.draw.textlength(label, font=foot)
        self.draw.text(((PAGE_W - w) / 2, PAGE_H - MARGIN_BOTTOM + 55),
                       label, font=foot, fill=MUTED)

        path = os.path.join(self.work_dir, f'manual_{self.page_no:03d}.png')
        # img2pdf は pHYs（DPI）からページサイズを決めるので必ず埋め込む
        self.img.save(path, 'PNG', dpi=(DPI, DPI))
        self.paths.append(path)

    def need(self, height: float) -> None:
        """height 分の余白を確保する。入らなければ改ページ。"""
        if self.y + height > CONTENT_BOTTOM:
            self._finish_page()
            self._new_page()

    def close(self) -> list[str]:
        self._finish_page()
        return self.paths


def _render(blocks: list[dict], work_dir: str) -> list[str]:
    page = _Layout(work_dir)

    for block in blocks:
        kind = block['type']

        if kind == 'h1':
            fonts = _fonts(SIZE_H1)
            lines = _wrap(page.draw, _runs(block['text']), fonts, CONTENT_W)
            lh = SIZE_H1 * 1.5
            page.need(len(lines) * lh + 40)
            for line in lines:
                _draw_line(page.draw, MARGIN_X, page.y, line, fonts)
                page.y += lh
            page.y += 10
            page.draw.line([(MARGIN_X, page.y), (PAGE_W - MARGIN_X, page.y)],
                           fill=ACCENT, width=3)
            page.y += 30

        elif kind == 'h2':
            fonts = _fonts(SIZE_H2)
            lines = _wrap(page.draw, _runs(block['text']), fonts, CONTENT_W - 20)
            lh = SIZE_H2 * 1.5
            # 見出しだけがページ末尾に取り残されないよう、次の 1 行分も確保する
            page.need(len(lines) * lh + 50)
            page.y += 22
            top = page.y
            for line in lines:
                _draw_line(page.draw, MARGIN_X + 18, page.y, line, fonts)
                page.y += lh
            page.draw.rectangle([MARGIN_X, top + 2, MARGIN_X + 6, page.y - 6],
                                fill=ACCENT)
            page.y += 16

        elif kind == 'h3':
            fonts = _fonts(SIZE_H3)
            lines = _wrap(page.draw, _runs(block['text']), fonts, CONTENT_W)
            lh = SIZE_H3 * 1.5
            page.need(len(lines) * lh + 45)
            page.y += 16
            for line in lines:
                _draw_line(page.draw, MARGIN_X, page.y, line, fonts, ACCENT)
                page.y += lh
            page.y += 8

        elif kind == 'para':
            fonts = _fonts(SIZE_BODY)
            lines = _wrap(page.draw, _runs(block['text']), fonts, CONTENT_W)
            lh = SIZE_BODY * LINE_RATIO
            for line in lines:
                page.need(lh)
                _draw_line(page.draw, MARGIN_X, page.y, line, fonts)
                page.y += lh
            page.y += 10

        elif kind == 'li':
            fonts = _fonts(SIZE_BODY)
            lh = SIZE_BODY * LINE_RATIO
            marker = block['marker']
            indent = block['indent'] * 28
            hang = page.draw.textlength(marker + ' ', font=fonts['normal'])
            x = MARGIN_X + indent
            lines = _wrap(page.draw, _runs(block['text']), fonts,
                          CONTENT_W - indent - hang)
            for i, line in enumerate(lines):
                page.need(lh)
                if i == 0:
                    page.draw.text((x, page.y), marker,
                                   font=fonts['normal'], fill=MUTED)
                _draw_line(page.draw, x + hang, page.y, line, fonts)
                page.y += lh
            page.y += 6

        elif kind == 'quote':
            fonts = _fonts(SIZE_BODY)
            lh = SIZE_BODY * LINE_RATIO
            lines = _wrap(page.draw, _runs(block['text']), fonts, CONTENT_W - 30)
            page.need(len(lines) * lh + 20)
            top = page.y
            for line in lines:
                _draw_line(page.draw, MARGIN_X + 26, page.y, line, fonts, MUTED)
                page.y += lh
            page.draw.rectangle([MARGIN_X, top, MARGIN_X + 4, page.y - 4],
                                fill=RULE)
            page.y += 14

        elif kind == 'code':
            mono = _font('mono', SIZE_CODE)
            lh = SIZE_CODE * 1.6
            lines = block['lines']
            height = len(lines) * lh + 28
            page.need(height)
            page.draw.rectangle(
                [MARGIN_X, page.y, PAGE_W - MARGIN_X, page.y + height - 8],
                fill=CODE_BG)
            y = page.y + 14
            for line in lines:
                page.draw.text((MARGIN_X + 16, y), line, font=mono, fill=CODE_INK)
                y += lh
            page.y += height + 10

        elif kind == 'table':
            _render_table(page, block['rows'])

    return page.close()


def _render_table(page: _Layout, rows: list[list[str]]) -> None:
    if not rows:
        return

    fonts = _fonts(SIZE_TABLE)
    lh = SIZE_TABLE * 1.6
    pad = 12
    cols = max(len(r) for r in rows)
    rows = [r + [''] * (cols - len(r)) for r in rows]

    # 列幅は「中身の自然幅」の比で配分する。1 列が極端に痩せないよう下限を置く。
    natural = []
    for c in range(cols):
        widest = max(
            page.draw.textlength(re.sub(r'[*`]', '', r[c]), font=fonts['normal'])
            for r in rows)
        natural.append(max(widest, 60))

    total = sum(natural)
    widths = [max(CONTENT_W * n / total, CONTENT_W * 0.14) for n in natural]
    scale = CONTENT_W / sum(widths)
    widths = [w * scale for w in widths]

    for i, row in enumerate(rows):
        cells = [_wrap(page.draw, _runs(text), fonts, widths[c] - pad * 2)
                 for c, text in enumerate(row)]
        height = max(len(lines) for lines in cells) * lh + pad * 2

        page.need(height)
        # ヘッダ行はページを跨いだら描き直したいところだが、
        # README の表は短いので単純に行単位の改ページのみとする。
        top = page.y
        if i == 0:
            page.draw.rectangle(
                [MARGIN_X, top, PAGE_W - MARGIN_X, top + height],
                fill=TABLE_HEAD_BG)

        x = MARGIN_X
        for c, lines in enumerate(cells):
            y = top + pad
            for line in lines:
                _draw_line(page.draw, x + pad, y, line, fonts)
                y += lh
            page.draw.rectangle([x, top, x + widths[c], top + height],
                                outline=RULE, width=1)
            x += widths[c]

        page.y = top + height

    page.y += 16


# --- 公開関数 -----------------------------------------------------------------
def build_manual_pdf(source_path: str, output_path: str) -> str:
    """MANUAL.md から使い方 PDF を生成し、書き出したパスを返す。"""
    with open(source_path, encoding='utf-8') as f:
        md = f.read()

    blocks = _parse(md)
    if not blocks:
        raise RuntimeError(f'{source_path} から本文を抽出できませんでした')

    work_dir = tempfile.mkdtemp(prefix='manual_pdf_')
    try:
        pages = _render(blocks, work_dir)
        return build_pdf(pages, str(output_path), QUALITY_HIGH)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == '__main__':
    root = os.path.dirname(os.path.abspath(__file__))
    out = build_manual_pdf(os.path.join(root, 'MANUAL.md'),
                           os.path.join(root, 'dist', '使い方.pdf'))
    print(f'生成: {out}')
