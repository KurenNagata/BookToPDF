
"""純粋ロジックのユニットテスト（GUI・実画面キャプチャは対象外）。

    python -m pytest tests -v
"""

from __future__ import annotations

import os
import sys

import pytest
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture_engine import (  # noqa: E402
    CHANGE_RATIO,
    DIRECTION_KEYS,
    OUTPUT_MODES,
    changed_fraction,
    fingerprint,
    signature_diff,
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
