"""Палитра, тема и мелкие SVG-хелперы — общие для всех генераторов.

Светлая и тёмная темы живут внутри одного SVG: значения объявлены
CSS-переменными, тёмные переопределяются через `prefers-color-scheme`.
Так работает и в README на github.com, где картинки подключены через <img>.
"""

from __future__ import annotations

WIDE = 620  # ширина «широких» картинок в README

# &apos; — потому что строка уходит в атрибут в двойных кавычках
MONO = (
    "ui-monospace,SFMono-Regular,Menlo,Consolas,"
    "&apos;Liberation Mono&apos;,monospace"
)

LIGHT = {
    "fg": "#1f2328",
    "muted": "#59636e",
    "dim": "#8c959f",
    "line": "#d8dee4",
    "accent": "#1a7f37",
    "ink": "#57606a",
    "h0": "#ebedf0",
    "h1": "#aceebb",
    "h2": "#4ac26b",
    "h3": "#2da44e",
    "h4": "#116329",
}

DARK = {
    "fg": "#e6edf3",
    "muted": "#8b949e",
    "dim": "#6e7681",
    "line": "#30363d",
    "accent": "#3fb950",
    "ink": "#adbac7",
    "h0": "#151b23",
    "h1": "#033a16",
    "h2": "#196c2e",
    "h3": "#2ea043",
    "h4": "#56d364",
}

HEAT = ("var(--h0)", "var(--h1)", "var(--h2)", "var(--h3)", "var(--h4)")


def css_vars() -> str:
    light = "".join(f"--{k}:{v};" for k, v in LIGHT.items())
    dark = "".join(f"--{k}:{v};" for k, v in DARK.items())
    return f":root{{{light}}}@media(prefers-color-scheme:dark){{:root{{{dark}}}}}"


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def document(width: float, height: float, body: str, css: str = "") -> str:
    """Собрать законченный SVG-файл."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{num(width)}" height="{num(height)}" '
        f'viewBox="0 0 {num(width)} {num(height)}" '
        f'font-family="{MONO}">'
        f"<style>{css_vars()}{css}</style>"
        f"{body}</svg>"
    )


def num(value: float) -> str:
    """Короткая запись числа: 14.0 -> 14, 10.75 -> 10.75."""
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text or "0"


def xlist(values) -> str:
    return " ".join(num(v) for v in values)


def thousands(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def text(
    x,
    y,
    content: str,
    *,
    size: float,
    fill: str = "var(--fg)",
    weight: int | None = None,
    anchor: str | None = None,
    opacity: float | None = None,
    extra: str = "",
    letter_spacing: float | None = None,
    raw: bool = False,
) -> str:
    """<text>. x может быть числом или списком координат (по символу)."""
    coord = xlist(x) if isinstance(x, (list, tuple)) else num(x)
    parts = [f'<text x="{coord}" y="{num(y)}" font-size="{num(size)}" fill="{fill}"']
    if weight:
        parts.append(f' font-weight="{weight}"')
    if anchor:
        parts.append(f' text-anchor="{anchor}"')
    if opacity is not None:
        parts.append(f' opacity="{num(opacity)}"')
    if letter_spacing is not None:
        parts.append(f' letter-spacing="{num(letter_spacing)}"')
    if extra:
        parts.append(" " + extra)
    parts.append(">")
    parts.append(content if raw else esc(content))
    parts.append("</text>")
    return "".join(parts)


def hidden_until(attr: str, begin: float, dur: float, to: float, spline: bool = False) -> str:
    """Появление из нуля с задержкой — и чтобы оно пережило отсутствие SMIL.

    У самого элемента атрибут остаётся конечным (opacity=1, width=итог):
    рендерер без SMIL — превью в редакторе, растеризатор — покажет
    готовый кадр, а не пустоту. Проигрывающий же сначала применит <set>
    и обнулит атрибут, а с момента begin им управляет <animate>, который
    стоит позже по документу и потому перебивает <set>.

    Без <set> элемент был бы виден с нулевой секунды и на своей задержке
    только моргал — то есть «печать» превращалась в рябь по готовому.
    """
    ease = (
        ' calcMode="spline" keySplines="0.2 0.7 0.2 1" keyTimes="0;1"'
        if spline
        else ""
    )
    return (
        f'<set attributeName="{attr}" to="0" begin="0s"/>'
        f'<animate attributeName="{attr}" from="0" to="{num(to)}" '
        f'begin="{num(begin)}s" dur="{num(dur)}s" fill="freeze"{ease}/>'
    )


def fade_in(begin: float, dur: float = 0.45, to: float = 1.0) -> str:
    """SMIL-проявление. Скрипты GitHub из README вырезает, SMIL — нет."""
    return hidden_until("opacity", begin, dur, to)


def grow(attr: str, to: float, begin: float, dur: float = 0.7) -> str:
    return hidden_until(attr, begin, dur, to, spline=True)
