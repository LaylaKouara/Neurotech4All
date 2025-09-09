# app/app.py
import os
import json
import random
from flask import Flask, render_template, request, abort, url_for
from pathlib import Path
import re, yaml
from dateutil import parser as dateparser
import markdown as md


app = Flask(__name__)
app.config['FREEZER_MODE'] = False  # development default

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/overview.html')
def overview():
    return render_template('overview.html')

@app.route('/team.html')
def team():
    team_path = os.path.join(app.root_path, 'static', 'data', 'team.json')
    with open(team_path, encoding='utf-8') as f:
        members = json.load(f)
    random.shuffle(members)
    return render_template('team.html', members=members)

@app.route('/resources.html')
def resources():
    return render_template('resources.html')

@app.route('/contact.html')
def contact():
    return render_template('contact.html')

# ------------------ NEWS SECTION ------------------
from flask import url_for, request

@app.template_filter("asset")
def asset_url(p: str) -> str:
    """
    Image/asset URL that works in both modes:
      - Dev server: absolute (/static/...)
      - Frozen HTML (file://): relative with proper ../ depth
    Accepts 'images/x.jpg', 'static/images/x.jpg', or absolute URLs.
    """
    if not p:
        return ""
    p = str(p).strip().replace("\\", "/").lstrip("/")

    # Pass through absolute URLs and data URIs
    if p.lower().startswith(("http://", "https://", "data:")):
        return p

    # Normalize to be under /static/
    if p.startswith("static/"):
        p = p[7:]

    if app.config.get("FREEZER_MODE"):
        # Compute depth from the current request path (e.g., '/news/foo.html' -> 1)
        depth = request.path.strip("/").count("/")
        prefix = "../" * depth
        return f"{prefix}static/{p}"

    # Dev: absolute URL served by Flask
    return url_for("static", filename=p)

@app.template_filter("relurl")
def relurl(p: str) -> str:
    """
    Make internal links relative when freezing (so file:// works).
    Use with url_for(...) in templates: {{ url_for('endpoint')|relurl }}.
    """
    if not p:
        return ""
    s = str(p).strip()

    # Absolute external links pass through
    if s.lower().startswith(("http://", "https://", "mailto:", "data:")):
        return s

    # Strip leading slash for internal paths
    if s.startswith("/"):
        s = s[1:]

    if app.config.get("FREEZER_MODE"):
        depth = request.path.strip("/").count("/")
        prefix = "../" * depth
        return f"{prefix}{s}"

    # Dev: keep as-is (usually '/path')
    return p

FM_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)\Z", re.S)

def _news_dir() -> Path:
    d = Path(app.root_path) / "static" / "data" / "news"
    if not d.exists():
        abort(404, f"News folder not found: {d}")
    return d

def _iter_md_paths():
    for p in sorted(_news_dir().glob("**/*.md")):
        if p.is_file() and p.stem.lower() != "news-template":
            yield p

def _load_md(path: Path):
    m = FM_RE.match(path.read_text(encoding="utf-8"))
    if not m:
        raise ValueError(f"Front matter not found in {path.name}")
    meta = yaml.safe_load(m.group(1)) or {}
    body_md = m.group(2).strip()
    return meta, body_md

def _parse_date(meta: dict):
    date_obj = None
    if meta.get("date"):
        try:
            date_obj = dateparser.parse(str(meta["date"])).date()
        except Exception:
            pass
    date_str = date_obj.strftime("%d %b %Y").lstrip("0") if date_obj else ""
    return date_obj, date_str

def _make_teaser(meta: dict, body_md: str, limit: int = 240) -> str:
    teaser = (meta.get("teaser") or "").strip()
    if teaser:
        return teaser
    first_para = next((p.strip() for p in body_md.split("\n\n") if p.strip()), "")
    return (first_para[:limit] + "…") if len(first_para) > limit else first_para

def _reading_time(meta: dict, body_md: str) -> int:
    if meta.get("reading_time"):
        return int(meta["reading_time"])
    words = len(re.findall(r"\w+", body_md))
    return max(1, round(words / 200))

# ------------------ NEWS INDEX (contents page) ------------------
@app.route('/news_contents.html')
def news():
    """Build a news index from Markdown files with YAML front matter."""
    items = []
    for path in _iter_md_paths():
        try:
            meta, body_md = _load_md(path)
            title = meta.get("title") or path.stem.replace("-", " ").title()
            date_obj, date_str = _parse_date(meta)
            teaser = _make_teaser(meta, body_md)
            reading_time = _reading_time(meta, body_md)
            hero = meta.get("hero") or {}

            items.append({
                "title": title,
                "date": date_obj,
                "date_str": date_str,
                "author": meta.get("author", ""),
                "teaser": teaser,
                "reading_time": reading_time,
                "tags": meta.get("tags") or [],
                "slug": path.stem,
                "url": url_for("news_post", slug=path.stem),  # will be made relative in template
                "hero_src": (hero.get("src") or ""),
                "hero_alt": hero.get("alt", ""),
            })
        except Exception as e:
            print(f"[news] Skipping {path}: {e}")

    items.sort(key=lambda x: (x["date"] is not None, x["date"]), reverse=True)
    return render_template("news_contents.html", news_items=items)

# ------------------ SINGLE POST PAGE ------------------
@app.route("/news/<slug>.html")
def news_post(slug):
    path = next((p for p in _iter_md_paths() if p.stem == slug), None)
    if not path:
        abort(404)

    meta, body_md = _load_md(path)
    _date_obj, date_str = _parse_date(meta)

    body_html = md.markdown(
        body_md,
        extensions=["fenced_code", "tables", "attr_list", "smarty", "toc"]
    )

    # Canonical URL: front-matter permalink if present, else SITE_ORIGIN + page path
    if meta.get("permalink"):
        canonical = meta["permalink"].strip()
    else:
        rel_path = url_for("news_post", slug=slug).lstrip("/")  # e.g., news/my-post.html
        origin = (app.config.get("SITE_ORIGIN") or request.url_root).rstrip("/")
        canonical = f"{origin}/{rel_path}"

    return render_template(
        "news_post.html",
        slug=slug,
        body_html=body_html,
        date_str=date_str,
        canonical=canonical,  # 👈 add this
        **meta,
    )

if __name__ == '__main__':
    app.run(debug=True)
