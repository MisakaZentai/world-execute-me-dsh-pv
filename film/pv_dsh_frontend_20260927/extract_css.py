"""Collect dsh's own stylesheets for a standalone page: the component CSS strings of each client package (theme
tokens included) and the DisclosureRow class names from the web frontend build. Reads the packages under film/vendor/."""
import json
import re
from pathlib import Path

NM = Path(__file__).resolve().parents[1].joinpath("vendor")
PACKAGES = ["dsh-client-ui-theme", "dsh-client-ui-chat", "dsh-client-ui-tool", "dsh-client-ui-conversation",
            "dsh-client-ui-message-feedback", "dsh-client-ui-deliverables", "dsh-client-ui-layout"]
CSS_RE = re.compile(r'(?:const css(?:\$\d+)?|var \w+_css_default) = ("(?:[^"\\]|\\.)*");')


def package_css(name):
    src = (NM / name / "lib" / "client.js").read_text(encoding="utf8")
    return [json.loads(m.group(1)) for m in CSS_RE.finditer(src)]


def disclosure_map():
    """Resolve the DisclosureRow CSS-module map to real class names from the minified bundle."""
    js = next((NM / "dsh-web-frontend/dist/assets").glob("index-*.js")).read_text(encoding="utf8")
    m = re.search(r"U1=\{root:(\w+),row:(\w+),leading:(\w+),iconIdle:(\w+),chevronHover:(\w+),title:(\w+)\}", js)
    keys = ["root", "row", "leading", "iconIdle", "chevronHover", "title"]
    out = {}
    for k, sym in zip(keys, m.groups()):
        out[k] = re.search(r"[,; ]%s=\"([^\"]+)\"" % re.escape(sym), js).group(1)
    return out


if __name__ == "__main__":
    parts = []
    for p in PACKAGES:
        css = package_css(p)
        parts.append(f"/* {p}: {len(css)} blocks */\n" + "\n".join(css))
        print(p, len(css))
    Path("dsh_components.css").write_text("\n".join(parts), encoding="utf8")
    Path("disclosure_map.json").write_text(json.dumps(disclosure_map(), indent=1), encoding="utf8")
    print(Path("disclosure_map.json").read_text())
