"""画像群を 1 つの PDF に結合する。

品質 3 段階:
  高画質 … PNG を img2pdf でそのまま結合（再エンコードなし・無劣化）
  標準   … 0.85 倍に縮小 → JPEG q=85
  軽量   … 0.60 倍に縮小 → JPEG q=70

標準 / 軽量で作る一時 JPEG は必ず削除する（try/finally）。
"""

from __future__ import annotations

import os
import tempfile

import img2pdf
from PIL import Image

QUALITY_HIGH = '高画質'
QUALITY_NORMAL = '標準'
QUALITY_LIGHT = '軽量'

QUALITY_CHOICES = [QUALITY_HIGH, QUALITY_NORMAL, QUALITY_LIGHT]

# quality -> (縮小率, JPEG 品質)。None は再エンコードなし。
QUALITY_PRESETS: dict[str, tuple[float, int] | None] = {
    QUALITY_HIGH: None,
    QUALITY_NORMAL: (0.85, 85),
    QUALITY_LIGHT: (0.60, 70),
}


def build_pdf(image_paths: list[str], output_path: str,
              quality: str = QUALITY_HIGH) -> str:
    """image_paths を 1 つの PDF に結合し、実際に書き出したパスを返す。"""
    if not image_paths:
        raise ValueError('結合する画像がありません')

    if not output_path.lower().endswith('.pdf'):
        output_path += '.pdf'

    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    preset = QUALITY_PRESETS.get(quality, None)

    # 高画質: PNG をそのまま結合する
    if preset is None:
        with open(output_path, 'wb') as f:
            f.write(img2pdf.convert([str(p) for p in image_paths]))
        return output_path

    # 標準 / 軽量: 縮小 + JPEG 化してから結合する
    scale, jpeg_quality = preset
    tmp_dir = tempfile.mkdtemp(prefix='snap2pdf_jpeg_')
    tmp_files: list[str] = []
    try:
        for i, path in enumerate(image_paths):
            with Image.open(path) as im:
                im = im.convert('RGB')
                width = max(1, int(im.width * scale))
                height = max(1, int(im.height * scale))
                im = im.resize((width, height), Image.LANCZOS)

                tmp_path = os.path.join(tmp_dir, f'page_{i:04d}.jpg')
                im.save(tmp_path, 'JPEG', quality=jpeg_quality, optimize=True)
                tmp_files.append(tmp_path)

        with open(output_path, 'wb') as f:
            f.write(img2pdf.convert(tmp_files))
        return output_path
    finally:
        for tmp_path in tmp_files:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
