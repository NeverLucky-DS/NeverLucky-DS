"""ascii.svg — портрет, набранный символами.

Исходник — portrait.png рядом с README, а если его нет, аватарка
профиля: она качается во время прогона с github.com/<логин>.png, так что
портрет обновится сам после её смены. Ровный фон вырезается заливкой от
краёв: всё, что дотягивается до рамки в пределах допуска по цвету,
считается фоном и не рисуется вовсе.

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
from PIL import Image, ImageFilter

from common import MONO, document, hidden_until, num, xlist

COLS = 132  # символов в ширину
CELL = 6.0  # шаг по горизонтали
LINE = 12.0  # шаг по строкам
FONT = CELL / 0.6  # у моноширинных шрифтов ширина знака = 0.6em
PAD = 14.0

RAMP = ".`':-=+*csS#%@"  # от «еле видно» к «залито»

WORK = 800  # размер, на котором ищем фон и считаем тон
TOL = 34.0  # допуск по цвету для заливки фона
COVER_MIN = 0.35  # ниже этой доли непрозрачности символ не рисуем
ROW_DUR = 0.06  # сколько «печатается» одна строка
ROW_START = 0.08  # анимация стартует не в нуле: иначе каретка первой строки
# «примерзает» в статичных превью, которые берут кадр на t=0


SOURCES = ("portrait.png", "portrait.jpg", "portrait.jpeg", "portrait.webp")


def fetch_avatar(login: str, size: int = 800) -> Image.Image:
    url = f"https://github.com/{login}.png?size={size}"
    response = requests.get(
        url, timeout=30, headers={"User-Agent": "profile-graphics"}
    )
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def load_source(login: str, root: str):
    """Портрет из репозитория, если он там лежит; иначе аватарка профиля.

    Аватарка — кадр на все случаи жизни, а рампу нужен снимок по пояс
    на ровном фоне. Поэтому исходник можно положить рядом: portrait.png
    в корне (или свой путь в PORTRAIT_SOURCE). Нет файла — работает
    прежняя схема, портрет обновляется вслед за аватаркой.
    """
    explicit = os.environ.get("PORTRAIT_SOURCE", "").strip()
    for path in [explicit] if explicit else [os.path.join(root, n) for n in SOURCES]:
        if path and os.path.exists(path):
            return Image.open(path).convert("RGB"), os.path.basename(path)
    return fetch_avatar(login), f"github.com/{login}.png"


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


FLAT_MIX = 0.7  # доля «выровненной» яркости против исходной
GAMMA = 1.7  # >1 — светлее, лицо уходит в разреженную часть рампа


def tone(work: Image.Image, fore: np.ndarray) -> np.ndarray:
    """Яркость 0..1, подготовленная под рамп.

    Портрет освещён неровно, и этот перепад через весь кадр крупнее любой
    черты лица: после обычной нормировки одна щека уходит в плотные
    символы, вторая в пустоту, а глаза и рот теряются между ними. Поэтому
    низкие частоты (сам перепад) вычитаются, а средний уровень
    возвращается на место — остаётся то, что рампу и нужно рисовать.

    Размывать приходится по картинке, где фон заменён средним по силуэту:
    иначе белое поле затекает под контур и по краю лица появляется кайма.
    """
    gray = work.convert("L").filter(
        ImageFilter.UnsharpMask(radius=2, percent=80, threshold=1)
    )
    plane = np.asarray(gray, dtype=np.float32) / 255.0

    inside = fore > 0.5
    if inside.sum() < 64:
        return plane

    mean = float(plane[inside].mean())
    filled = Image.fromarray(
        np.clip(np.where(inside, plane, mean) * 255.0, 0, 255).astype(np.uint8)
    )
    low_freq = (
        np.asarray(
            filled.filter(ImageFilter.GaussianBlur(work.width / 9.6)),
            dtype=np.float32,
        )
        / 255.0
    )
    plane = FLAT_MIX * (plane - low_freq + mean) + (1.0 - FLAT_MIX) * plane

    low, high = np.percentile(plane[inside], (1.5, 98.5))
    if high - low > 1e-3:
        plane = np.clip((plane - low) / (high - low), 0.0, 1.0)
    return np.clip(plane, 0.0, 1.0)


ACCENT_SAT = 0.40  # ниже этой насыщенности цвет считаем нейтральным
ACCENT_WARM = 95.0  # 0..95° — кожа, волосы, хаки; всё остальное цветное
ACCENT_MIN = 10  # меньше клеток — шум, акцента нет


def _hue(colours: np.ndarray) -> np.ndarray:
    """Оттенок в градусах, без покомпонентных циклов."""
    red, green, blue = colours[..., 0], colours[..., 1], colours[..., 2]
    top = colours.max(-1)
    spread = top - colours.min(-1)
    lit = spread > 1e-6

    from_red = lit & (top == red)
    from_green = lit & (top == green) & ~from_red
    from_blue = lit & ~from_red & ~from_green

    hue = np.zeros_like(top)
    hue[from_red] = ((green - blue)[from_red] / spread[from_red]) % 6.0
    hue[from_green] = (blue - red)[from_green] / spread[from_green] + 2.0
    hue[from_blue] = (red - green)[from_blue] / spread[from_blue] + 4.0
    return (hue * 60.0) % 360.0


def _denoise(mask: np.ndarray, need: int = 2) -> np.ndarray:
    """Выбросить одиночные клетки: губы и блики — не деталь одежды."""
    height, width = mask.shape
    padded = np.pad(mask.astype(np.int16), 1)
    neighbours = sum(
        padded[1 + dy : 1 + dy + height, 1 + dx : 1 + dx + width]
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if (dy, dx) != (0, 0)
    )
    return mask & (neighbours >= need)


def accents(colours: np.ndarray):
    """Клетки цветной детали одежды и её усреднённый цвет.

    Портрет рисуется одним цветом, но галстук в кадре — единственное
    по-настоящему цветное пятно, и терять его жалко. Кожа, волосы и
    свитер укладываются в тёплый сектор оттенков; всё, что за его
    пределами и достаточно насыщено, и есть цветная деталь.
    """
    top = colours.max(-1)
    spread = top - colours.min(-1)
    saturation = np.where(top > 1e-6, spread / np.maximum(top, 1e-6), 0.0)
    mask = (saturation >= ACCENT_SAT) & (top > 0.12) & (_hue(colours) > ACCENT_WARM)
    mask = _denoise(mask)
    if mask.sum() < ACCENT_MIN:
        return np.zeros_like(mask), None
    return mask, np.median(colours[mask], axis=0)


def _shift(colour: np.ndarray, value: float, saturation: float) -> str:
    """Тот же оттенок, подогнанный по яркости и насыщенности под тему."""
    top = float(colour.max())
    if top < 1e-6:
        return "#000000"
    grey = np.full(3, top, dtype=np.float32)
    tinted = grey + (np.asarray(colour, dtype=np.float32) - grey) * saturation
    scaled = np.clip(tinted * (value / top), 0.0, 1.0)
    return "#" + "".join(f"{round(float(c) * 255):02x}" for c in scaled)


def _box_resize(plane: np.ndarray, cols: int, rows: int) -> np.ndarray:
    image = Image.fromarray(np.clip(plane * 255.0, 0, 255).astype(np.uint8))
    return np.asarray(image.resize((cols, rows), Image.Resampling.BOX), dtype=np.float32) / 255.0


def to_grid(img: Image.Image, cols: int = COLS):
    """Картинка -> (символы, маска акцента, цвет акцента). Пробел не рисуем."""
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

    ink = np.clip(1.0 - shade, 0.0, 1.0) ** GAMMA
    level = np.clip(np.rint(ink * (len(RAMP) - 1)).astype(int), 0, len(RAMP) - 1)

    colours = np.stack(
        [
            _box_resize(np.asarray(work, np.float32)[..., i] / 255.0 * fore, cols, rows)
            / np.maximum(cover, 1e-3)
            for i in range(3)
        ],
        axis=-1,
    )
    colourful, accent = accents(np.clip(colours, 0.0, 1.0))

    drawn = cover >= COVER_MIN
    grid = [
        [RAMP[level[r, c]] if drawn[r, c] else " " for c in range(cols)]
        for r in range(rows)
    ]
    return grid, (colourful & drawn), accent


def trim(grid: list[list[str]], mask: np.ndarray):
    rows = [i for i, r in enumerate(grid) if any(ch != " " for ch in r)]
    if not rows:
        return grid, mask
    left = min(next(i for i, ch in enumerate(grid[r]) if ch != " ") for r in rows)
    right = max(
        len(grid[r]) - next(i for i, ch in enumerate(reversed(grid[r])) if ch != " ")
        for r in rows
    )
    keep = slice(rows[0], rows[-1] + 1)
    return [r[left:right] for r in grid[keep]], mask[keep, left:right]


def render(grid: list[list[str]], mask: np.ndarray, accent, alt: str) -> str:
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
        base = num(top + LINE * 0.78)

        clips.append(
            f'<clipPath id="r{index}"><rect x="{num(start)}" y="{num(top)}" '
            f'height="{num(LINE)}" width="{num(end - start)}">'
            + hidden_until("width", begin, ROW_DUR, end - start)
            + "</rect></clipPath>"
        )

        runs = [("p", [m for m in marks if not mask[index, m[0]]])]
        if accent is not None:
            runs.append(("a", [m for m in marks if mask[index, m[0]]]))
        body.append(f'<g clip-path="url(#r{index})">')
        for css_class, run in runs:
            if not run:
                continue
            body.append(
                f'<text class="{css_class}" '
                f'x="{xlist(PAD + c * CELL for c, _ in run)}" y="{base}">'
                + "".join(ch for _, ch in run)
                + "</text>"
            )
        body.append("</g>")
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

    css = f".p{{fill:var(--ink)}}text{{font-size:{num(FONT)}px}}"
    if accent is not None:
        # на белом цвет берём как есть, на тёмном поднимаем яркость,
        # иначе бордовый сливается с фоном
        css += (
            f":root{{--tint:{_shift(accent, 0.46, 1.0)}}}"
            "@media(prefers-color-scheme:dark)"
            f"{{:root{{--tint:{_shift(accent, 0.74, 0.88)}}}}}"
            ".a{fill:var(--tint)}"
        )
    svg = document(width, height, "".join(clips) + "".join(body), css)
    return svg.replace(
        f'font-family="{MONO}">', f'font-family="{MONO}"><title>{alt}</title>', 1
    )


def build(login: str, root: str) -> str:
    image, origin = load_source(login, root)
    cells, colourful, accent = to_grid(image)
    grid, mask = trim(cells, colourful)
    svg = render(grid, mask, accent, f"ASCII-портрет @{login}")
    with open(os.path.join(root, "ascii.svg"), "w", encoding="utf-8") as handle:
        handle.write(svg)
    print(f"ascii.svg готов — из {origin}, {len(grid)} строк")
    return svg


def main() -> None:
    login = os.environ.get("PROFILE_LOGIN") or (
        sys.argv[1] if len(sys.argv) > 1 else ""
    )
    if not login:
        raise SystemExit("нужен логин: PROFILE_LOGIN=... или аргументом")
    build(login, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


if __name__ == "__main__":
    main()
