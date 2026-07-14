
"""純粋ロジックのユニットテスト（GUI・実画面キャプチャは対象外）。

    python -m pytest tests -v
"""

from __future__ import annotations

import os
import sys

import pytest
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import capture_engine  # noqa: E402
from capture_engine import (  # noqa: E402
    CHANGE_RATIO,
    DIRECTION_KEYS,
    OUTPUT_MODES,
    CaptureEngine,
    changed_fraction,
    fingerprint,
    signature_diff,
)
from paths import (  # noqa: E402
    MAX_NAME_LENGTH,
    default_output_dir,
    sanitize_folder_name,
)
from pdf_builder import (  # noqa: E402
    QUALITY_HIGH,
    QUALITY_LIGHT,
    QUALITY_NORMAL,
    build_pdf,
)


@pytest.fixture
def png_pages(tmp_path):
    """写真的なダミーページ 3 枚。

    AC-06（軽量 < 標準 < 高画質）は「写真的な画像」を前提とする仕様のため、
    滑らかなグラデーション + ぼかしたノイズ + 図形で写真らしい画像を作る。
    値を % 256 で折り返すような合成パターンは PNG が極端に小さく圧縮され、
    JPEG よりも小さくなってしまうので使わない。
    """
    paths = []
    for i in range(3):
        image = Image.new('RGB', (400, 300))
        pixels = image.load()
        for x in range(400):
            for y in range(300):
                pixels[x, y] = (int(255 * x / 400),
                                int(255 * y / 300),
                                int(255 * (x + y) / 700))

        noise = (Image.effect_noise((400, 300), 40)
                 .convert('L')
                 .filter(ImageFilter.GaussianBlur(1.5)))
        image = Image.blend(image, Image.merge('RGB', (noise, noise, noise)), 0.25)

        draw = ImageDraw.Draw(image)
        draw.ellipse([40 + i * 30, 40, 200 + i * 30, 200], fill=(200, 60 + i * 40, 90))
        image = image.filter(ImageFilter.GaussianBlur(0.8))

        path = tmp_path / f'page_{i:04d}.png'
        image.save(path, 'PNG')
        paths.append(str(path))
    return paths


# --------------------------------------------------------------- build_pdf
@pytest.mark.parametrize('quality', [QUALITY_HIGH, QUALITY_NORMAL, QUALITY_LIGHT])
def test_build_pdf_creates_pdf(png_pages, tmp_path, quality):
    output = str(tmp_path / f'out_{quality}.pdf')
    result = build_pdf(png_pages, output, quality)

    assert result == output
    assert os.path.exists(result)
    assert os.path.getsize(result) > 0
    with open(result, 'rb') as f:
        assert f.read(5) == b'%PDF-'


def test_build_pdf_appends_pdf_extension(png_pages, tmp_path):
    result = build_pdf(png_pages, str(tmp_path / 'no_extension'), QUALITY_HIGH)

    assert result.endswith('.pdf')
    assert os.path.exists(result)


def test_build_pdf_creates_output_directory(png_pages, tmp_path):
    output = str(tmp_path / 'nested' / 'deeper' / 'out.pdf')
    result = build_pdf(png_pages, output, QUALITY_NORMAL)

    assert os.path.exists(result)


def test_build_pdf_leaves_no_temp_jpeg(png_pages, tmp_path):
    """標準 / 軽量で作った一時 JPEG が残らないこと。"""
    for quality in (QUALITY_NORMAL, QUALITY_LIGHT):
        build_pdf(png_pages, str(tmp_path / f'{quality}.pdf'), quality)

    leftovers = [p for p in tmp_path.rglob('*') if p.suffix.lower() in ('.jpg', '.jpeg')]
    assert leftovers == []
    assert [p for p in png_pages if os.path.exists(p)] == png_pages  # 入力は消さない


def test_build_pdf_size_order(png_pages, tmp_path):
    """軽量 < 標準 < 高画質 の順にファイルサイズが小さいこと。"""
    sizes = {}
    for quality in (QUALITY_HIGH, QUALITY_NORMAL, QUALITY_LIGHT):
        path = build_pdf(png_pages, str(tmp_path / f'{quality}.pdf'), quality)
        sizes[quality] = os.path.getsize(path)

    assert sizes[QUALITY_LIGHT] < sizes[QUALITY_NORMAL] < sizes[QUALITY_HIGH]


def test_build_pdf_rejects_empty_list(tmp_path):
    with pytest.raises(ValueError):
        build_pdf([], str(tmp_path / 'empty.pdf'))


# ------------------------------------------------------- fingerprint / diff
def test_diff_of_identical_images_is_zero():
    image = Image.new('RGB', (200, 150), (30, 90, 180))
    assert signature_diff(fingerprint(image), fingerprint(image)) == 0.0


def test_diff_of_different_images_is_large():
    black = fingerprint(Image.new('RGB', (200, 150), (0, 0, 0)))
    white = fingerprint(Image.new('RGB', (200, 150), (255, 255, 255)))
    assert signature_diff(black, white) >= 50


def test_diff_with_none_is_max():
    sig = fingerprint(Image.new('RGB', (10, 10), (10, 20, 30)))
    assert signature_diff(sig, None) == 255.0
    assert signature_diff(None, sig) == 255.0


def test_fingerprint_length_is_32x32():
    assert len(fingerprint(Image.new('RGB', (640, 480), (1, 2, 3)))) == 32 * 32


# ---------------------------------------------------------- changed_fraction
def _slide(lines: int) -> Image.Image:
    """箇条書きスライドを模擬。lines 行の本文を持つ。"""
    im = Image.new('RGB', (800, 600), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([60, 40, 460, 80], fill=(25, 25, 25))            # タイトル
    for i in range(lines):
        d.rectangle([60, 140 + i * 40, 380, 150 + i * 40], fill=(40, 40, 40))
    return im


def test_changed_fraction_identical_is_zero():
    sig = fingerprint(_slide(3))
    assert changed_fraction(sig, sig) == 0.0


def test_changed_fraction_none_is_max():
    sig = fingerprint(_slide(3))
    assert changed_fraction(sig, None) == 1.0
    assert changed_fraction(None, sig) == 1.0


def test_one_added_bullet_is_detected_as_change():
    """箇条書きが 1 行増えただけのページを「変わった」と判定できること。

    平均差 (signature_diff) はこの差を既定しきい値 3 未満に均してしまう
    （= 旧方式ではページ送りが飛ぶ原因）。変化画素割合なら確実に拾える。
    """
    a = fingerprint(_slide(3))
    b = fingerprint(_slide(4))

    assert signature_diff(a, b) < 3           # 旧方式では「同じ」扱いだった
    assert changed_fraction(a, b) >= CHANGE_RATIO   # 新方式は「変わった」と判定


def test_cursor_blink_is_not_a_change():
    """カーソル点滅程度の微小変化は「ページが変わった」とみなさないこと。"""
    base = _slide(3)
    blink = base.copy()
    ImageDraw.Draw(blink).rectangle([300, 300, 302, 316], fill=(0, 0, 0))

    assert changed_fraction(fingerprint(base), fingerprint(blink)) < CHANGE_RATIO


# ------------------------------------------------------------ OUTPUT_MODES
def test_output_modes_cover_pdf_and_png():
    assert OUTPUT_MODES['PDFのみ'] == ('pdf',)
    assert OUTPUT_MODES['画像 (PNG) のみ'] == ('png',)
    assert set(OUTPUT_MODES['PDF + 画像 (PNG)']) == {'pdf', 'png'}


# ------------------------------------------------------------ DIRECTION_KEYS
def test_manual_direction_maps_to_none():
    assert DIRECTION_KEYS['なし（手動でめくる）'] is None


def test_arrow_directions_are_keys():
    for label in ('右 (→)', '左 (←)', '下 (↓)'):
        assert DIRECTION_KEYS[label] is not None


# ------------------------------------------------------ sanitize_folder_name
def test_folder_name_keeps_normal_name():
    assert sanitize_folder_name('数学の教科書 第1章') == '数学の教科書 第1章'


def test_folder_name_replaces_invalid_characters():
    assert sanitize_folder_name('a/b:c*d?') == 'a_b_c_d_'


def test_folder_name_drops_trailing_dot_and_space():
    """Windows は末尾の '.' と空白を黙って落とす。先に落として名前をずらさない。"""
    assert sanitize_folder_name('  第1章. ') == '第1章'


def test_folder_name_escapes_reserved_device_name():
    assert sanitize_folder_name('NUL') == '_NUL'
    assert sanitize_folder_name('con.txt') == '_con.txt'


def test_folder_name_is_truncated():
    assert len(sanitize_folder_name('あ' * 300)) == MAX_NAME_LENGTH


@pytest.mark.parametrize('name', ['', None, '   ', '...', '  ..  '])
def test_folder_name_falls_back_to_empty(name):
    """既定名 (capture_日時) に落とすため、成立しない名前は '' を返す。"""
    assert sanitize_folder_name(name) == ''


# ----------------------------------------------------------- default_output_dir
def test_default_output_dir_exists():
    path = default_output_dir()
    assert os.path.isdir(path)


# ------------------------------------------------------------ _make_output_dir
def _engine(**config) -> CaptureEngine:
    return CaptureEngine(config, on_status=lambda _t: None, on_done=lambda _p: None)


def test_make_output_dir_uses_given_name(tmp_path):
    out = _engine()._make_output_dir(str(tmp_path), '第1章')

    assert os.path.basename(out) == '第1章'
    assert os.path.isdir(out)


def test_make_output_dir_defaults_to_timestamp(tmp_path):
    out = _engine()._make_output_dir(str(tmp_path), '')

    assert os.path.basename(out).startswith('capture_')
    assert os.path.isdir(out)


def test_make_output_dir_never_overwrites(tmp_path):
    """同じ名前で 2 回撮っても、前回の結果を上書きしないこと。"""
    first = _engine()._make_output_dir(str(tmp_path), '第1章')
    second = _engine()._make_output_dir(str(tmp_path), '第1章')

    assert first != second
    assert os.path.basename(second) == '第1章_2'
    assert os.path.isdir(first) and os.path.isdir(second)


def test_make_output_dir_sanitizes_name(tmp_path):
    out = _engine()._make_output_dir(str(tmp_path), 'a/b')

    assert os.path.dirname(out) == str(tmp_path)   # サブフォルダを掘らせない
    assert os.path.basename(out) == 'a_b'


# ------------------------------------------------- 末尾判定 (_await_page_change)
class _FakeRaw:
    def __init__(self, image: Image.Image):
        self.size = image.size
        self.bgra = image.convert('RGBA').tobytes('raw', 'BGRA')


class _FakeSct:
    """grab() のたびに frames を 1 枚ずつ返す。尽きたら最後の 1 枚を返し続ける。"""

    def __init__(self, frames):
        self.frames = list(frames)
        self.grabs = 0

    def grab(self, _region):
        image = self.frames[min(self.grabs, len(self.frames) - 1)]
        self.grabs += 1
        return _FakeRaw(image)


class _FakeKeyboard:
    def __init__(self):
        self.sends = 0

    def press(self, _key):
        self.sends += 1

    def release(self, _key):
        pass


_REGION = {'left': 0, 'top': 0, 'width': 200, 'height': 150}


def _viewer_page(n: int, turning: bool = False) -> Image.Image:
    """ページ n の表示。turning=True はめくり途中（アニメーション）のフレーム。"""
    im = Image.new('RGB', (200, 150), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([20, 20, 180, 60 + (n % 4) * 15], fill=(30, 30, 30))
    if turning:
        d.rectangle([0, 0, 200, 20], fill=(120, 120, 120))
    return im


@pytest.fixture
def fast_engine(monkeypatch):
    """待ち時間を詰めた CaptureEngine（末尾判定を実時間で待たない）。"""
    for name, value in (('CHANGE_TIMEOUT', 0.15), ('STABLE_TIMEOUT', 0.15),
                        ('POLL_INTERVAL', 0.01), ('KEY_HOLD', 0.0)):
        monkeypatch.setattr(capture_engine, name, value)
    return _engine(dup_threshold=3)


def _await(engine, frames):
    keyboard = _FakeKeyboard()
    last_sig = fingerprint(frames[0])
    image, sig = engine._await_page_change(
        _FakeSct(frames), _REGION, keyboard, capture_engine.Key.right,
        last_sig, min_wait=0.0)
    return image, sig, keyboard


def test_page_turn_is_captured(fast_engine):
    """めくれたら、アニメーションではなく落ち着いた後のページを返すこと。"""
    frames = [_viewer_page(1), _viewer_page(2, turning=True), _viewer_page(2)]

    image, sig, _ = _await(fast_engine, frames)

    assert image is not None
    assert changed_fraction(sig, fingerprint(_viewer_page(2))) == 0.0


def test_bounce_at_end_of_book_is_not_a_new_page(fast_engine):
    """末尾でめくろうとして画面が一瞬揺れ、同じページに戻る場合。

    揺れを「ページが変わった」と受け取って撮ってしまうと、同じページを最大
    ページ数まで撮り続けて止まらなくなる。落ち着いた先が直前ページと同じなら
    ページは進んでいないと見なし、末尾と判定すること。
    """
    # 揺れ (turning) は一瞬で、すぐ元のページに戻って静止する
    frames = [_viewer_page(7), _viewer_page(7, turning=True),
              _viewer_page(7), _viewer_page(7)] * 200

    image, _, keyboard = _await(fast_engine, frames)

    assert image is None                              # 末尾と判定した
    assert keyboard.sends == capture_engine.MAX_KEY_RESENDS   # 送り直しはした


def test_static_end_of_book_stops(fast_engine):
    """末尾で画面がまったく変わらない場合も、送り直したうえで停止すること。"""
    image, _, keyboard = _await(fast_engine, [_viewer_page(9)])

    assert image is None
    assert keyboard.sends == capture_engine.MAX_KEY_RESENDS
