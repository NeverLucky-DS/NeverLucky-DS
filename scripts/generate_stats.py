"""Все графики профиля: тепловая карта, стрики, языки, год посимвольно
и картинки-заголовки для разделов README.

Заголовки — именно картинки: GitHub вырезает из README и скрипты, и CSS,
так что своим шрифтом и цветом их иначе не нарисовать. Анимация — SMIL
внутри SVG по той же причине.
"""

from __future__ import annotations

import datetime as dt
import math
import os
import sys

from common import (
    HEAT,
    WIDE,
    document,
    esc,
    fade_in,
    grow,
    num,
    text,
    thousands,
    xlist,
)
from github_data import collect

PAD = 16.0
MONTHS = (
    "янв фев мар апр май июн июл авг сен окт ноя дек".split()
)
YEAR_RAMP = "·:+#@"
# бледные зелёные из тепловой карты на белом почти не видны —
# в посимвольном году громкость передаём прозрачностью акцента
YEAR_FILL = (
    ("var(--line)", 1.0),
    ("var(--accent)", 0.4),
    ("var(--accent)", 0.62),
    ("var(--accent)", 0.82),
    ("var(--accent)", 1.0),
)


def plural(count: int, one: str, few: str, many: str) -> str:
    tens = count % 100
    ones = count % 10
    if 11 <= tens <= 14:
        return many
    if ones == 1:
        return one
    if 2 <= ones <= 4:
        return few
    return many


def ru_date(iso: str) -> str:
    day = dt.date.fromisoformat(iso)
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def level_scale(counts):
    """Порог уровня 1..4 по квантилям ненулевых дней."""
    active = sorted(c for c in counts if c > 0)
    if not active:
        return lambda value: 0

    def at(fraction: float) -> int:
        return active[min(len(active) - 1, int(len(active) * fraction))]

    t1, t2, t3 = at(0.4), at(0.7), at(0.9)

    def level(value: int) -> int:
        if value <= 0:
            return 0
        if value <= t1:
            return 1
        if value <= t2:
            return 2
        if value <= t3:
            return 3
        return 4

    return level


# --------------------------------------------------------------------- stats


def stats_svg(data: dict) -> str:
    weeks = data["weeks"]
    level = level_scale(c for week in weeks for _, c in week)

    label_w = 26.0
    x0 = PAD + label_w
    step = (WIDE - x0 - PAD) / len(weeks)
    cell = step - 1.9
    top = 84.0
    height = 194.0

    year = data["year"]
    total = thousands(year["total"])
    body = [
        text(PAD, 46, total, size=27, weight=600),
        text(
            PAD + len(total) * 27 * 0.6 + 8,
            46,
            "контрибуций за год",
            size=12.5,
            fill="var(--muted)",
        ),
        text(
            WIDE - PAD,
            46,
            f"{ru_date(data['weeks'][0][0][0])} — {ru_date(data['today'])}",
            size=11,
            fill="var(--dim)",
            anchor="end",
        ),
    ]

    for index, week in enumerate(weeks):
        first = dt.date.fromisoformat(week[0][0])
        # подпись у той недели, с которой месяц начинается, — ровно одна на месяц
        if first.day <= 7 and index < len(weeks) - 1:
            body.append(
                text(
                    x0 + index * step,
                    top - 8,
                    MONTHS[first.month - 1],
                    size=10,
                    fill="var(--dim)",
                )
            )

    for row, name in ((1, "Пн"), (3, "Ср"), (5, "Пт")):
        body.append(
            text(
                PAD,
                top + row * step + cell * 0.78,
                name,
                size=9.5,
                fill="var(--dim)",
            )
        )

    for index, week in enumerate(weeks):
        for date, count in week:
            row = dt.date.fromisoformat(date).weekday()
            row = (row + 1) % 7  # GitHub рисует неделю с воскресенья
            body.append(
                f'<rect x="{num(x0 + index * step)}" '
                f'y="{num(top + row * step)}" width="{num(cell)}" '
                f'height="{num(cell)}" rx="2" fill="{HEAT[level(count)]}">'
                f"{fade_in(0.2 + index * 0.014)}"
                f"<title>{esc(f'{ru_date(date)}: {count}')}</title></rect>"
            )

    foot = top + 7 * step + 22
    facts = " · ".join(
        (
            f"{thousands(year['commits'])} "
            f"{plural(year['commits'], 'коммит', 'коммита', 'коммитов')}",
            f"{thousands(year['prs'])} PR",
            f"{thousands(year['issues'])} issue",
            f"{thousands(year['reviews'])} "
            f"{plural(year['reviews'], 'ревью', 'ревью', 'ревью')}",
        )
    )
    body.append(text(PAD, foot, facts, size=11, fill="var(--muted)"))

    legend_x = WIDE - PAD - 5 * 13 - 46
    body.append(
        text(legend_x, foot, "меньше", size=10, fill="var(--dim)", anchor="end")
    )
    for i, colour in enumerate(HEAT):
        body.append(
            f'<rect x="{num(legend_x + 6 + i * 13)}" y="{num(foot - 8)}" '
            f'width="9" height="9" rx="2" fill="{colour}"/>'
        )
    body.append(
        text(legend_x + 6 + 5 * 13, foot, "больше", size=10, fill="var(--dim)")
    )

    return document(WIDE, height, "".join(body))


# -------------------------------------------------------------------- streak


def streak_svg(data: dict) -> str:
    streak = data["streak"]
    height = 148.0
    third = WIDE / 3

    def span(start, end) -> str:
        if not start:
            return "—"
        if start == end:
            return ru_date(start)
        return f"{ru_date(start)} — {ru_date(end)}"

    panels = (
        (
            thousands(streak["current"]),
            plural(streak["current"], "день подряд", "дня подряд", "дней подряд"),
            span(streak["current_from"], streak["current_to"]),
            True,
        ),
        (
            thousands(streak["longest"]),
            "самая длинная серия",
            span(streak["longest_from"], streak["longest_to"]),
            False,
        ),
        (
            thousands(streak["total"]),
            "контрибуций всего",
            f"с {ru_date(data['created'])}",
            False,
        ),
    )

    body = []
    for index in (1, 2):
        x = third * index
        body.append(
            f'<line x1="{num(x)}" y1="30" x2="{num(x)}" y2="{num(height - 26)}" '
            'stroke="var(--line)" stroke-width="1"/>'
        )

    radius = 36.0
    ring = 2 * math.pi * radius
    for index, (value, label, note, marked) in enumerate(panels):
        cx = third * (index + 0.5)
        if marked:
            body.append(
                f'<circle cx="{num(cx)}" cy="60" r="{num(radius)}" fill="none" '
                'stroke="var(--line)" stroke-width="2"/>'
            )
            body.append(
                f'<circle cx="{num(cx)}" cy="60" r="{num(radius)}" fill="none" '
                'stroke="var(--accent)" stroke-width="2" stroke-linecap="round" '
                f'stroke-dasharray="{num(ring)}" stroke-dashoffset="0" '
                f'transform="rotate(-90 {num(cx)} 60)">'
                f'<animate attributeName="stroke-dashoffset" from="{num(ring)}" '
                'to="0" begin="0.15s" dur="1.1s" fill="freeze" calcMode="spline" '
                'keySplines="0.2 0.7 0.2 1" keyTimes="0;1"/></circle>'
            )
        body.append(
            f"<g>{fade_in(0.35)}"
            + text(
                cx,
                69,
                value,
                size=30,
                weight=600,
                anchor="middle",
                fill="var(--accent)" if marked else "var(--fg)",
            )
            + "</g>"
        )
        body.append(
            text(cx, 112, label, size=12, anchor="middle", fill="var(--muted)")
        )
        body.append(
            text(cx, 130, note, size=10, anchor="middle", fill="var(--dim)")
        )

    return document(WIDE, height, "".join(body))


# --------------------------------------------------------------------- langs


PALETTE = (
    "#3572A5",
    "#f1e05a",
    "#e34c26",
    "#563d7c",
    "#89e051",
    "#b07219",
    "#00ADD8",
    "#dea584",
)


def _colour(name: str, index: int, known: dict) -> str:
    return known.get(name) or PALETTE[index % len(PALETTE)]


def _block(title: str, items, top: float, colours: dict, delay: float):
    """Заголовок + полоса + легенда. Возвращает (svg, высота блока)."""
    total = sum(value for _, value in items) or 1
    top_items = list(items[:6])
    rest = total - sum(value for _, value in top_items)
    rows = [(name, value) for name, value in top_items]
    if rest > 0:
        rows.append(("прочее", rest))

    bar_w = WIDE - PAD * 2
    bar_y = top + 12
    body = [text(PAD, top + 4, title, size=11.5, fill="var(--muted)")]

    body.append(
        f'<clipPath id="round{int(top)}"><rect x="{num(PAD)}" y="{num(bar_y)}" '
        f'width="{num(bar_w)}" height="11" rx="5.5"/></clipPath>'
        f'<clipPath id="wipe{int(top)}"><rect x="{num(PAD)}" y="{num(bar_y)}" '
        f'height="11" width="{num(bar_w)}">'
        f'{grow("width", bar_w, delay, 0.9)}</rect></clipPath>'
        f'<g clip-path="url(#round{int(top)})">'
        f'<g clip-path="url(#wipe{int(top)})">'
    )
    offset = PAD
    for index, (name, value) in enumerate(rows):
        width = bar_w * value / total
        body.append(
            f'<rect x="{num(offset)}" y="{num(bar_y)}" width="{num(width + 0.6)}" '
            f'height="11" fill="{_colour(name, index, colours)}"/>'
        )
        offset += width
    body.append("</g></g>")

    # легенда «течёт» по строке и переносится сама — названия языков разной длины
    x, y = PAD, bar_y + 32
    for index, (name, value) in enumerate(rows):
        share = f"{100.0 * value / total:.1f}%".replace(".0%", "%")
        name_w = len(name) * 11.5 * 0.62
        item_w = 14 + name_w + 8 + len(share) * 11 * 0.62
        if x > PAD and x + item_w > WIDE - PAD:
            x, y = PAD, y + 19
        body.append(
            f"<g>{fade_in(delay + 0.25 + index * 0.05)}"
            f'<circle cx="{num(x + 4)}" cy="{num(y - 4)}" r="4" '
            f'fill="{_colour(name, index, colours)}"/>'
            + text(x + 14, y, name, size=11.5)
            + text(x + 14 + name_w + 8, y, share, size=11, fill="var(--dim)")
            + "</g>"
        )
        x += item_w + 20
    return "".join(body), (y + 8) - top


def langs_svg(data: dict) -> str:
    colours = data.get("lang_colours", {})
    top = PAD + 8
    first, height = _block(
        f"по объёму кода · {data['repos']} "
        + plural(data["repos"], "публичный репозиторий", "публичных репозитория", "публичных репозиториев"),
        data["langs_bytes"],
        top,
        colours,
        0.1,
    )
    second_top = top + height + 26
    second, height2 = _block(
        "по числу репозиториев · основной язык",
        data["langs_repos"],
        second_top,
        colours,
        0.35,
    )
    return document(WIDE, second_top + height2 + PAD, first + second)


# ---------------------------------------------------------------------- year


def year_svg(data: dict) -> str:
    weeks = data["weeks"]
    level = level_scale(c for week in weeks for _, c in week)

    step = (WIDE - PAD * 2) / len(weeks)
    font = 13.0
    line = 15.0
    top = 44.0

    cells: dict[tuple[int, int], list[float]] = {}
    for index, week in enumerate(weeks):
        for date, count in week:
            row = (dt.date.fromisoformat(date).weekday() + 1) % 7
            cells.setdefault((row, level(count)), []).append(
                PAD + index * step + (step - font * 0.6) / 2
            )

    body = [
        text(
            PAD,
            26,
            "последние 12 месяцев, один символ на день",
            size=11.5,
            fill="var(--muted)",
        )
    ]
    for (row, lvl), xs in sorted(cells.items()):
        fill, alpha = YEAR_FILL[lvl]
        body.append(
            f'<text x="{xlist(xs)}" y="{num(top + row * line)}" '
            f'font-size="{num(font)}" fill="{fill}" fill-opacity="{num(alpha)}">'
            f"{fade_in(0.15 + lvl * 0.12)}"
            + YEAR_RAMP[lvl] * len(xs)
            + "</text>"
        )

    foot = top + 7 * line + 16
    body.append(text(PAD, foot, "тише", size=10, fill="var(--dim)"))
    for index, char in enumerate(YEAR_RAMP):
        fill, alpha = YEAR_FILL[index]
        body.append(
            text(
                PAD + 30 + index * 12,
                foot,
                char,
                size=12,
                fill=fill,
                extra=f'fill-opacity="{num(alpha)}"',
            )
        )
    body.append(
        text(PAD + 30 + len(YEAR_RAMP) * 12 + 4, foot, "громче", size=10, fill="var(--dim)")
    )
    return document(WIDE, foot + PAD, "".join(body))


# ------------------------------------------------------------------ headings

HEADINGS = {
    "hd-about": "о себе",
    "hd-stack": "стек",
    "hd-projects": "проекты",
    "hd-stats": "статистика",
    "hd-how": "как это сделано",
    "hd-contacts": "контакты",
}


def heading_svg(label: str) -> str:
    size = 15.0
    spacing = 1.6
    advance = size * 0.6 + spacing
    end = 15 + len(label) * advance + 10
    body = (
        '<rect x="0" y="7" width="3" height="16" rx="1.5" fill="var(--accent)"/>'
        + text(15, 21, label, size=size, weight=600, letter_spacing=spacing)
        + f'<line x1="{num(end)}" y1="15" x2="{num(WIDE)}" y2="15" '
        'stroke="var(--line)" stroke-width="1">'
        f'<animate attributeName="x2" from="{num(end)}" to="{num(WIDE)}" '
        'begin="0.1s" dur="0.8s" fill="freeze" calcMode="spline" '
        'keySplines="0.2 0.7 0.2 1" keyTimes="0;1"/></line>'
    )
    return document(WIDE, 30, body)


# ---------------------------------------------------------------------- main


def write(root: str, name: str, content: str) -> None:
    path = os.path.join(root, name)
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            old = handle.read()
    if old == content:
        print(f"  = {name}")
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    print(f"  * {name}")


def main() -> None:
    login = (
        os.environ.get("PROFILE_LOGIN")
        or os.environ.get("GITHUB_REPOSITORY_OWNER")
        or (sys.argv[1] if len(sys.argv) > 1 else "")
    )
    if not login:
        raise SystemExit("нужен логин: GITHUB_REPOSITORY_OWNER / аргументом")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = collect(login)

    write(root, "stats.svg", stats_svg(data))
    write(root, "streak.svg", streak_svg(data))
    write(root, "langs.svg", langs_svg(data))
    write(root, "year.svg", year_svg(data))
    for name, label in HEADINGS.items():
        write(root, f"{name}.svg", heading_svg(label))


if __name__ == "__main__":
    main()
