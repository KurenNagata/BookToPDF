"""OwlBunko の本棚フォルダへの保存（保存先の既定値と、PDF の置き方）。

    python -m pytest tests -v
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import capture_engine  # noqa: E402
import paths  # noqa: E402
from capture_engine import OUTPUT_MODES, CaptureEngine  # noqa: E402
from paths import default_output_dir, is_library_dir, owlbunko_library_dir  # noqa: E402


# ------------------------------------------------ 保存先の既定値
def _write_settings(appdata, library_dir) -> None:
    folder = appdata / 'OwlBunko'
    folder.mkdir(parents=True)
    (folder / 'settings.json').write_text(
        json.dumps({'library_dir': library_dir}, ensure_ascii=False), encoding='utf-8')


def test_library_dir_comes_from_the_owlbunko_settings(tmp_path):
    library = tmp_path / '本棚'
    library.mkdir()
    appdata = tmp_path / 'appdata'
    _write_settings(appdata, str(library))
    found = owlbunko_library_dir({'APPDATA': str(appdata)}, home=str(tmp_path / 'home'))
    assert found == os.path.normpath(str(library))


def test_library_dir_falls_back_to_the_default_folder_only_if_it_exists(tmp_path):
    home = tmp_path / 'home'
    home.mkdir()
    env = {'APPDATA': str(tmp_path / 'none')}   # 設定ファイルがない
    assert owlbunko_library_dir(env, home=str(home)) is None   # OwlBunko を使っていない
    (home / 'OwlBunko').mkdir()
    assert owlbunko_library_dir(env, home=str(home)) == os.path.normpath(
        str(home / 'OwlBunko'))
    assert list((home / 'OwlBunko').iterdir()) == []   # フォルダには、何も作らない


@pytest.mark.parametrize('content', ['{ broken', '[1, 2]', '{"library_dir": 5}',
                                     '{"library_dir": "  "}'])
def test_library_dir_ignores_broken_settings(tmp_path, content):
    appdata = tmp_path / 'appdata'
    (appdata / 'OwlBunko').mkdir(parents=True)
    (appdata / 'OwlBunko' / 'settings.json').write_text(content, encoding='utf-8')
    assert owlbunko_library_dir({'APPDATA': str(appdata)}, home=str(tmp_path)) is None


def test_settings_folder_that_does_not_exist_is_skipped(tmp_path):
    appdata = tmp_path / 'appdata'
    _write_settings(appdata, str(tmp_path / '抜いたドライブ'))   # 実際にはない
    home = tmp_path / 'home'
    (home / 'OwlBunko').mkdir(parents=True)
    assert owlbunko_library_dir({'APPDATA': str(appdata)}, home=str(home)) == (
        os.path.normpath(str(home / 'OwlBunko')))


def test_default_output_dir_prefers_the_library(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'owlbunko_library_dir', lambda *a, **k: str(tmp_path))
    assert default_output_dir() == str(tmp_path)
    monkeypatch.setattr(paths, 'owlbunko_library_dir', lambda *a, **k: None)
    assert os.path.isdir(default_output_dir())   # ダウンロード（これまでどおり）


def test_is_library_dir_ignores_trailing_separators_and_case(tmp_path):
    library = tmp_path / 'OwlBunko'
    library.mkdir()
    assert is_library_dir(str(library) + os.sep, library=str(library))
    assert is_library_dir(str(library).upper(), library=str(library)) == (os.name == 'nt')
    assert not is_library_dir(str(tmp_path / 'other'), library=str(library))
    assert not is_library_dir(str(library), library='')
    assert not is_library_dir('', library=str(library))


# ------------------------------------------------ 本棚フォルダへの保存
def _engine() -> CaptureEngine:
    return CaptureEngine({}, on_status=lambda _t: None, on_done=lambda _p: None)


def _pages(tmp_path, count=2):
    out = []
    for index in range(count):
        path = tmp_path / f'src_{index}.png'
        Image.new('RGB', (200, 300), (index * 40, 100, 150)).save(path)
        out.append(str(path))
    return out


def _save(tmp_path, base, name='本の題名', mode='PDF + 画像 (PNG)'):
    cfg = {'output_base': str(base), 'output_name': name, 'output_mode': mode,
           'quality': 'high'}
    return _engine()._save_to_library(_pages(tmp_path), OUTPUT_MODES[mode], cfg)


def test_library_save_puts_the_pdf_directly_under_the_library(tmp_path):
    library = tmp_path / 'lib'
    library.mkdir()
    path, failure = _save(tmp_path, library)
    assert failure is None
    assert path == str(library / '本の題名.pdf')   # 題名がファイル名になる
    with open(path, 'rb') as f:
        assert f.read(5) == b'%PDF-'
    assert sorted(p.name for p in library.iterdir()) == ['本の題名.pdf', '本の題名_images']
    images = library / '本の題名_images'
    assert sorted(p.name for p in images.iterdir()) == ['src_0.png', 'src_1.png']
    assert not (library / '.booktopdf-tmp').exists()   # 一時の置き場は、残らない


def test_library_save_pdf_only_makes_no_images_folder(tmp_path):
    library = tmp_path / 'lib'
    library.mkdir()
    path, failure = _save(tmp_path, library, mode='PDFのみ')
    assert failure is None and [p.name for p in library.iterdir()] == ['本の題名.pdf']
    assert path.endswith('本の題名.pdf')


def test_library_save_png_only_goes_to_the_images_folder(tmp_path):
    library = tmp_path / 'lib'
    library.mkdir()
    path, failure = _save(tmp_path, library, mode='画像 (PNG) のみ')
    assert failure is None and path == str(library / '本の題名_images')
    assert [p.name for p in library.iterdir()] == ['本の題名_images']   # PDF は置かない


def test_library_save_never_overwrites_and_adds_numbers(tmp_path):
    library = tmp_path / 'lib'
    library.mkdir()
    first, _ = _save(tmp_path, library)
    second, _ = _save(tmp_path, library)
    third, _ = _save(tmp_path, library)
    assert [os.path.basename(p) for p in (first, second, third)] == [
        '本の題名.pdf', '本の題名_2.pdf', '本の題名_3.pdf']
    assert (library / '本の題名_2_images').is_dir()   # PDF と画像の番号がそろう


def test_library_save_skips_names_taken_by_a_folder_or_an_unfinished_file(tmp_path):
    library = tmp_path / 'lib'
    library.mkdir()
    (library / '本の題名_images').mkdir()                  # 画像のフォルダが先にある
    (library / '.booktopdf-tmp').mkdir()
    (library / '.booktopdf-tmp' / '本の題名_2.pdf').write_bytes(b'')   # 書きかけが先にある
    path, _ = _save(tmp_path, library)
    assert os.path.basename(path) == '本の題名_3.pdf'


def test_library_save_uses_a_timestamp_name_when_the_name_is_empty(tmp_path):
    library = tmp_path / 'lib'
    library.mkdir()
    path, _ = _save(tmp_path, library, name='')
    assert os.path.basename(path).startswith('capture_') and path.endswith('.pdf')


def test_the_pdf_is_written_in_a_hidden_folder_not_in_the_library_root(tmp_path, monkeypatch):
    """書き終えるまで、本棚が見る場所（直下）には置かない（書きかけを読ませないため）。"""
    library = tmp_path / 'lib'
    library.mkdir()
    seen = []
    real = capture_engine.build_pdf

    def spy(images, out_path, quality):
        seen.append(os.path.basename(out_path))
        assert os.path.dirname(out_path) == str(library / '.booktopdf-tmp')
        assert not any(p.suffix.lower() == '.pdf' for p in library.iterdir())
        return real(images, out_path, quality)

    monkeypatch.setattr(capture_engine, 'build_pdf', spy)
    _save(tmp_path, library)
    assert seen == ['本の題名.pdf']   # 隠しフォルダの中の同じ名前
    assert [p.name for p in library.iterdir()].count('本の題名.pdf') == 1


def test_library_save_cleans_up_and_keeps_the_images_when_the_pdf_fails(tmp_path, monkeypatch):
    library = tmp_path / 'lib'
    library.mkdir()

    def boom(images, out_path, quality):
        with open(out_path, 'wb') as f:
            f.write(b'half')   # 書きかけを残して失敗する
        raise RuntimeError('壊れた')

    monkeypatch.setattr(capture_engine, 'build_pdf', boom)
    path, failure = _save(tmp_path, library, mode='PDFのみ')
    assert failure and 'PDF作成に失敗' in failure and '壊れた' in failure
    assert path == str(library / '本の題名_images')   # 撮ったページは、失わせない
    assert sorted(p.name for p in (library / '本の題名_images').iterdir()) == [
        'src_0.png', 'src_1.png']
    assert [p.name for p in library.iterdir()] == ['本の題名_images']   # 書きかけも、隠しフォルダも消えている


@pytest.mark.skipif(os.name != 'nt', reason='Windows では、名前の変更が、先にある名前を上書きしない')
def test_finishing_the_pdf_does_not_overwrite_one_that_appeared_meanwhile(tmp_path):
    library = tmp_path / 'lib'
    library.mkdir()
    (library / '.booktopdf-tmp').mkdir()
    (library / '.booktopdf-tmp' / '本.pdf').write_bytes(b'new')
    (library / '本.pdf').write_bytes(b'old')   # 書いているあいだに、同じ名前ができた
    final = _engine()._finish_library_pdf(str(library), '本')
    assert os.path.basename(final) == '本_2.pdf'
    assert (library / '本.pdf').read_bytes() == b'old'
    assert (library / '本_2.pdf').read_bytes() == b'new'
