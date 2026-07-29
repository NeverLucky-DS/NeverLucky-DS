"""Графики профиля: тепловая карта контрибуций и картинки-заголовки
для разделов README.

Заголовки — именно картинки: GitHub вырезает из README и скрипты, и CSS,
так что своим шрифтом и цветом их иначе не нарисовать. Анимация — SMIL
внутри SVG по той же причине.
"""

from __future__ import annotations

import datetime as dt
import os
import sys

from common import HEAT, WIDE, document, esc, fade_in, num, text, thousands
from github_data import collect

PAD = 16.0
MONTHS = (
    "янв фев мар апр май июн июл авг сен окт ноя дек".split()
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


# ------------------------------------------------------------------ headings

HEADINGS = {
    "hd-about": "о себе",
    "hd-stack": "стек",
    "hd-projects": "проекты",
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
    for name, label in HEADINGS.items():
        write(root, f"{name}.svg", heading_svg(label))


if __name__ == "__main__":
    main()
