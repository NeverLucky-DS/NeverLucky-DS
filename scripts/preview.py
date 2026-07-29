"""Локальный просмотр: SVG -> PNG, чтобы не открывать браузер.

    python3 scripts/preview.py            # все картинки профиля
    python3 scripts/preview.py stats.svg  # только одну

Складывает PNG в preview/ (папка в .gitignore). Растеризаторы пробуются
по очереди: cairosvg, rsvg-convert, потом QuickLook (macOS, из коробки).
Проигрывать SMIL никто из них не умеет, но <set> на нулевой секунде
некоторые применяют — и картинка выходит пустой. Поэтому перед растром
эти <set> вырезаются: на PNG попадает последний кадр анимации.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

SCALE = 2  # ретиновый масштаб

# <set ... to="0" begin="0s"/> — то, что прячет элемент до его очереди
HIDER = re.compile(r'<set attributeName="[^"]+" to="0" begin="0s"\s*/>')


def size_of(path: str) -> tuple[int, int]:
    with open(path, encoding="utf-8") as handle:
        head = handle.read(700)
    width = re.search(r'width="([\d.]+)"', head)
    height = re.search(r'height="([\d.]+)"', head)
    if not width or not height:
        raise SystemExit(f"{path}: не нашёл width/height")
    return round(float(width.group(1))), round(float(height.group(1)))


def _cairosvg(src: str, dst: str, width: int, height: int) -> bool:
    try:
        import cairosvg  # noqa: PLC0415
    except ImportError:
        return False
    cairosvg.svg2png(
        url=src, write_to=dst, output_width=width * SCALE, output_height=height * SCALE
    )
    return True


def _rsvg(src: str, dst: str, width: int, height: int) -> bool:
    if not shutil.which("rsvg-convert"):
        return False
    subprocess.run(
        ["rsvg-convert", "-w", str(width * SCALE), "-o", dst, src],
        check=True,
    )
    return True


def _quicklook(src: str, dst: str, width: int, height: int) -> bool:
    """QuickLook рисует в квадрат — обрезаем лишнее по настоящей пропорции."""
    if not shutil.which("qlmanage"):
        return False
    side = max(width, height) * SCALE
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["qlmanage", "-t", "-s", str(side), "-o", tmp, src],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        made = [f for f in os.listdir(tmp) if f.endswith(".png")]
        if not made:
            return False
        from PIL import Image  # noqa: PLC0415

        image = Image.open(os.path.join(tmp, made[0])).convert("RGBA")
        scale = image.width / max(width, height)
        image.crop(
            (0, 0, round(width * scale), round(height * scale))
        ).save(dst)
    return True


def render(src: str, dst: str) -> str:
    width, height = size_of(src)
    with open(src, encoding="utf-8") as handle:
        final_frame = HIDER.sub("", handle.read())

    with tempfile.TemporaryDirectory() as tmp:
        flat = os.path.join(tmp, os.path.basename(src))
        with open(flat, "w", encoding="utf-8") as handle:
            handle.write(final_frame)
        for name, fn in (
            ("cairosvg", _cairosvg),
            ("rsvg-convert", _rsvg),
            ("quicklook", _quicklook),
        ):
            if fn(flat, dst, width, height):
                return name
    raise SystemExit(
        "нечем растеризовать: поставьте cairosvg (pip install cairosvg) "
        "или librsvg (brew install librsvg)"
    )


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    names = sys.argv[1:] or sorted(
        f for f in os.listdir(root) if f.endswith(".svg")
    )
    out = os.path.join(root, "preview")
    os.makedirs(out, exist_ok=True)

    for name in names:
        src = os.path.join(root, os.path.basename(name))
        if not os.path.exists(src):
            print(f"  ? {name} — нет такого файла")
            continue
        dst = os.path.join(out, os.path.basename(name)[:-4] + ".png")
        engine = render(src, dst)
        print(f"  -> preview/{os.path.basename(dst)}  ({engine})")


if __name__ == "__main__":
    main()
