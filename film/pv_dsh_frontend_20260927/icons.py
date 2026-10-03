"""Pull dsh's own icon components out of the minified web bundle and turn them into plain SVG markup."""
import re
from pathlib import Path

BUNDLE = next(Path(__file__).resolve().parents[1].joinpath("vendor/dsh-web-frontend/dist/assets").glob("index-*.js"))
ATTR = re.compile(r'(\w+):("(?:[^"\\]|\\.)*"|-?[\d.]+|!0|!1)')
SHAPE = re.compile(r'a\.jsxs?\("(path|rect|circle|ellipse|line|polyline|polygon)",\{([^{}]*)\}')
KEBAB = {"fillRule": "fill-rule", "clipRule": "clip-rule", "strokeWidth": "stroke-width",
         "strokeLinecap": "stroke-linecap", "strokeLinejoin": "stroke-linejoin", "fillOpacity": "fill-opacity",
         "strokeOpacity": "stroke-opacity"}
_src = None


def _bundle():
    global _src
    if _src is None:
        _src = BUNDLE.read_text(encoding="utf8")
    return _src


def _body(start):
    """The source of one arrow-function icon, from its name to the end of its expression."""
    s = _bundle()
    i = s.index("=>", start) + 2
    depth = 0
    for j in range(i, len(s)):
        c = s[j]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth < 0:
                return s[i:j]
        elif c == "," and depth == 0:
            return s[i:j]
    return s[i:]


def svg(name, size=None, cls=""):
    s = _bundle()
    sym = re.search(r"[{,]%s:(\w+)[,}]" % name, s).group(1)
    start = re.search(r"[,; ]%s=\(\{size:\w=(\d+)" % re.escape(sym), s)
    default = int(start.group(1))
    body = _body(start.start())
    view = re.search(r'viewBox:"([^"]+)"', body).group(1)
    size = size or default
    shapes = []
    for tag, attrs in SHAPE.findall(body):
        parts = []
        for k, v in ATTR.findall(attrs):
            if k in ("children", "key"):
                continue
            v = "true" if v == "!0" else "false" if v == "!1" else v.strip('"')
            parts.append(f'{KEBAB.get(k, k)}="{v}"')
        shapes.append(f"<{tag} {' '.join(parts)}/>")
    return (f'<svg width="{size}" height="{size}" class="{cls}" viewBox="{view}" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(shapes)}</svg>')


if __name__ == "__main__":
    for n in ["IconThinkOutline14", "IconChevronDownOutline14", "IconApiOutline14", "IconSparkle16",
              "IconGaugeOutline16", "IconDatabaseOutline16", "IconClockOutline16", "IconCopyOutline16",
              "IconBranchOutline16", "IconLikeOutline16", "IconDislikeOutline16", "IconPlusOutline16",
              "IconPaperclipOutline16", "IconSendOutline14"]:
        out = svg(n)
        print(n, len(out), out[:90])
