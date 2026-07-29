"""ascii.svg — портрет из аватарки, набранный символами.

Аватарка качается во время прогона с github.com/<логин>.png, поэтому
портрет обновляется сам, если сменить её в профиле. Ровный фон вырезается
заливкой от краёв: всё, что дотягивается до рамки в пределах допуска по
цвету, считается фоном и не рисуется вовсе.

Координата каждого символа проставлена явно (x-список у <text>), а не
через один textLength на строку — сетка не поедет от того, какой
моноширинный шрифт стоит у читателя.
"""

from __future__ import annotations

import io
import os
import sys

import numpy as np
import requests
from PIL import Image, ImageFilter, ImageOps

from common import MONO, document, num, xlist

COLS = 92  # символов в ширину
CELL = 6.0  # шаг по горизонтали
LINE = 12.0  # шаг по строкам
FONT = CELL / 0.6  # у моноширинных шрифтов ширина знака = 0.6em
PAD = 14.0

RAMP = ".`':-=+*csS#%@"  # от «еле видно» к «залито»

WORK = 384  # размер, на котором ищем фон
TOL = 34.0  # допуск по цвету для заливки фона
COVER_MIN = 0.35  # ниже этой доли непрозрачности символ не рисуем
ROW_DUR = 0.06  # сколько «печатается» одна строка
ROW_START = 0.08  # анимация стартует не в нуле: иначе каретка первой строки
# «примерзает» в статичных превью, которые берут кадр на t=0


def fetch_avatar(login: str, size: int = 800) -> Image.Image:
    url = f"https://github.com/{login}.png?size={size}"
    response = requests.get(
        url, timeout=30, headers={"User-Agent": "profile-graphics"}
    )
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def background_mask(rgb: np.ndarray, tol: float = TOL) -> np.ndarray:
    """True там, где фон: заливка от рамки по пикселям близкого цвета."""
    height, width, _ = rgb.shape
    pixels = rgb.astype(np.float32)

    ring = np.concatenate(
        [pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]], axis=0
    )
    seed = np.median(ring, axis=0)
    ring_dist = np.sqrt(((ring - seed) ** 2).sum(axis=1))
    if (ring_dist <= tol).mean() < 0.6:
        # рамка пёстрая — ровного фона нет, вырезать нечего
        return np.zeros((height, width), bool)

    close = np.sqrt(((pixels - seed) ** 2).sum(axis=2)) <= tol

    reach = np.zeros((height, width), bool)
    reach[0] = close[0]
    reach[-1] = close[-1]
    reach[:, 0] = close[:, 0]
    reach[:, -1] = close[:, -1]

    while True:
        grown = reach.copy()
        grown[1:] |= reach[:-1]
        grown[:-1] |= reach[1:]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        grown &= close
        if grown.sum() == reach.sum():
            break
        reach = grown

    if reach.mean() > 0.97:
        # съело всё изображение — значит допуск не по адресу
        return np.zeros((height, width), bool)
    return reach


def crop_box(img: Image.Image) -> Image.Image:
    """PORTRAIT_CROP="x0,y0,x1,y1" в долях кадра — если аватарка не портрет."""
    spec = os.environ.get("PORTRAIT_CROP", "").strip()
    if not spec:
        return img
    try:
        x0, y0, x1, y1 = (float(part) for part in spec.split(","))
    except ValueError:
        raise SystemExit(f"PORTRAIT_CROP: жду 4 доли через запятую, получил {spec!r}")
    width, height = img.size
    return img.crop(
        (round(x0 * width), round(y0 * height), round(x1 * width), round(y1 * height))
    )


def tone(work: Image.Image, fore: np.ndarray) -> np.ndarray:
    """Яркость 0..1, растянутая так, чтобы рамп использовался целиком."""
    gray = work.convert("L").filter(
        ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2)
    )
    # фотографии почти всегда сидят в узком диапазоне: подмешиваем эквализацию
    gray = Image.blend(gray, ImageOps.equalize(gray), 0.65)

    plane = np.asarray(gray, dtype=np.float32) / 255.0
    visible = plane[fore > 0.5]
    if visible.size:
        low, high = np.percentile(visible, (1.0, 99.0))
        if high - low > 1e-3:
            plane = np.clip((plane - low) / (high - low), 0.0, 1.0)
    return plane


def _box_resize(plane: np.ndarray, cols: int, rows: int) -> np.ndarray:
    image = Image.fromarray(np.clip(plane * 255.0, 0, 255).astype(np.uint8))
    return np.asarray(image.resize((cols, rows), Image.Resampling.BOX), dtype=np.float32) / 255.0


def to_grid(img: Image.Image, cols: int = COLS) -> list[list[str]]:
    """Картинка -> прямоугольник символов (пробел = не рисуем)."""
    img = crop_box(img)
    work = img.resize(
        (WORK, max(1, round(WORK * img.height / img.width))),
        Image.Resampling.LANCZOS,
    )
    rgb = np.asarray(work, dtype=np.uint8)

    fore = (~background_mask(rgb)).astype(np.float32)
    gray = tone(work, fore)

    rows = max(1, round(cols * (work.height / work.width) * (CELL / LINE)))
    cover = _box_resize(fore, cols, rows)
    lit = _box_resize(gray * fore, cols, rows)
    shade = np.where(cover > 1e-3, lit / np.maximum(cover, 1e-3), 1.0)

    ink = np.clip(1.0 - shade, 0.0, 1.0) ** 0.9
    level = np.rint(ink * (len(RAMP) - 1)).astype(int)
    level = np.clip(level, 0, len(RAMP) - 1)

    grid = []
    for r in range(rows):
        line = []
        for c in range(cols):
            line.append(" " if cover[r, c] < COVER_MIN else RAMP[level[r, c]])
        grid.append(line)
    return grid


def trim(grid: list[list[str]]) -> list[list[str]]:
    rows = [r for r in grid if any(ch != " " for ch in r)]
    if not rows:
        return grid
    left = min(next(i for i, ch in enumerate(r) if ch != " ") for r in rows)
    right = max(
        len(r) - next(i for i, ch in enumerate(reversed(r)) if ch != " ") for r in rows
    )
    return [r[left:right] for r in rows]


def render(grid: list[list[str]], alt: str) -> str:
    cols = max(len(r) for r in grid)
    width = PAD * 2 + cols * CELL
    height = PAD * 2 + len(grid) * LINE

    clips: list[str] = []
    body: list[str] = []
    for index, row in enumerate(grid):
        marks = [(c, ch) for c, ch in enumerate(row) if ch != " "]
        if not marks:
            continue
        top = PAD + index * LINE
        start = PAD + marks[0][0] * CELL
        end = PAD + (marks[-1][0] + 1) * CELL
        begin = ROW_START + index * ROW_DUR

        clips.append(
            # width сразу конечная, из нуля стартует анимация — без SMIL
            # (превью, растеризатор) картинка видна целиком, а не пустая
            f'<clipPath id="r{index}"><rect x="{num(start)}" y="{num(top)}" '
            f'height="{num(LINE)}" width="{num(end - start)}">'
            f'<animate attributeName="width" from="0" to="{num(end - start)}" '
            f'begin="{num(begin)}s" dur="{num(ROW_DUR)}s" fill="freeze"/>'
            "</rect></clipPath>"
        )
        body.append(
            f'<g clip-path="url(#r{index})"><text class="p" '
            f'x="{xlist(PAD + c * CELL for c, _ in marks)}" '
            f'y="{num(top + LINE * 0.78)}">'
            + "".join(ch for _, ch in marks)
            + "</text></g>"
        )
        # каретка, добегающая до конца строки
        body.append(
            f'<rect class="p" y="{num(top + LINE * 0.1)}" width="{num(CELL)}" '
            f'height="{num(LINE * 0.8)}" opacity="0">'
            f'<animate attributeName="x" from="{num(start)}" to="{num(end)}" '
            f'begin="{num(begin)}s" dur="{num(ROW_DUR)}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.75" begin="{num(begin)}s"/>'
            f'<set attributeName="opacity" to="0" begin="{num(begin + ROW_DUR)}s"/>'
            "</rect>"
        )

    css = f".p{{fill:var(--ink)}}text.p{{font-size:{num(FONT)}px}}"
    svg = document(width, height, "".join(clips) + "".join(body), css)
    return svg.replace(
        f'font-family="{MONO}">', f'font-family="{MONO}"><title>{alt}</title>', 1
    )


def build(login: str, out: str) -> str:
    grid = trim(to_grid(fetch_avatar(login)))
    svg = render(grid, f"ASCII-портрет @{login}")
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(svg)
    return svg


def main() -> None:
    login = os.environ.get("PROFILE_LOGIN") or (
        sys.argv[1] if len(sys.argv) > 1 else ""
    )
    if not login:
        raise SystemExit("нужен логин: PROFILE_LOGIN=... или аргументом")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build(login, os.path.join(root, "ascii.svg"))
    print("ascii.svg готов")


if __name__ == "__main__":
    main()
