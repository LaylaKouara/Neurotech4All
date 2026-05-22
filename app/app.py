# app/app.py
#
# Flask application for Neurotech4All.
# Runs in dev mode (python app/app.py) or is frozen to static HTML by freeze.py.
#
# Key design points:
#   - site_config.json drives nav links, footer columns, and partner logos so
#     editors never need to touch HTML templates.
#   - team.json drives the team section; add a row to add a team member.
#   - News posts are Markdown files in static/data/news/; each has YAML front matter.
#   - The `inject_config` context processor makes `config` available in every template.
#   - FREEZER_MODE=True switches asset/link helpers to emit relative URLs so the
#     frozen file:// site works without a web server.

import os
import json
import re
import random
from pathlib import Path
from datetime import datetime

import yaml
import markdown as md
from dateutil import parser as dateparser
from flask import Flask, render_template, request, abort, url_for

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# FREEZER_MODE is set to True by freeze.py before freezing.
# In development it stays False so Flask serves absolute /static/... URLs.
app.config['FREEZER_MODE'] = False

# ---------------------------------------------------------------------------
# Site-wide config (nav, footer, partners) injected into every template
# ---------------------------------------------------------------------------

def _load_site_config() -> dict:
    """Load site_config.json once at startup. Returns empty dict on failure."""
    cfg_path = Path(app.root_path) / "static" / "data" / "site_config.json"
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[config] Could not load site_config.json: {exc}")
        return {}

# Cache the config at module load time so it isn't re-read on every request.
_SITE_CONFIG = _load_site_config()

@app.context_processor
def inject_config():
    """Make `config` available in every Jinja2 template automatically."""
    return {"config": _SITE_CONFIG}

# ---------------------------------------------------------------------------
# Template filters: asset URLs and internal link helpers
# ---------------------------------------------------------------------------

@app.template_filter("asset")
def asset_url(p: str) -> str:
    """
    Return a URL for an image / static asset that works in both modes:
      - Dev server  -> absolute URL  e.g. /static/images/brain.png
      - Frozen HTML -> relative URL  e.g. ../static/images/brain.png

    Accepts any of:
      "images/brain.png"          (relative to static/)
      "static/images/brain.png"   (with static/ prefix)
      "https://..."               (passed through unchanged)
    """
    if not p:
        return ""
    p = str(p).strip().replace("\\", "/").lstrip("/")

    # Absolute URLs and data URIs pass straight through.
    if p.lower().startswith(("http://", "https://", "data:")):
        return p

    # Strip a leading "static/" so both forms normalise the same way.
    if p.startswith("static/"):
        p = p[7:]

    if app.config.get("FREEZER_MODE"):
        # How many directory levels deep is the current page?
        # E.g. /news/my-post.html has depth 1, so we need "../" once.
        depth = request.path.strip("/").count("/")
        prefix = "../" * depth
        return f"{prefix}static/{p}"

    return url_for("static", filename=p)


@app.template_filter("relurl")
def relurl(p: str) -> str:
    """
    Make an internal URL relative when freezing (so file:// navigation works).
    Usage in templates:  href="{{ url_for('news') | relurl }}"

    External URLs (http/https/mailto) pass through unchanged.
    """
    if not p:
        return ""
    s = str(p).strip()

    if s.lower().startswith(("http://", "https://", "mailto:", "data:")):
        return s

    # Strip the leading slash for internal paths.
    if s.startswith("/"):
        s = s[1:]

    if app.config.get("FREEZER_MODE"):
        depth = request.path.strip("/").count("/")
        prefix = "../" * depth
        return f"{prefix}{s}"

    return p


@app.template_filter("postprocess_body")
def postprocess_body(html: str) -> str:
    """
    Fix image src attributes inside rendered Markdown body HTML.

    News post Markdown files reference images with paths like:
        data/news/images/my-photo.jpg
    These need to become proper asset URLs so they resolve in both dev
    and frozen modes. This filter is applied to body_html in news_post.html.
    """
    def _replace(m):
        raw = m.group(1)
        # Already absolute, leave alone.
        if raw.lower().startswith(("http://", "https://", "data:", "/")):
            return m.group(0)
        return f'src="{asset_url(raw)}"'

    return re.sub(r'src="([^"]*)"', _replace, html)

# ---------------------------------------------------------------------------
# News helpers
# ---------------------------------------------------------------------------

# Regex that matches the YAML front matter block at the top of a Markdown file.
FM_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)\Z", re.S)


def _news_dir() -> Path:
    """Return the path to the news Markdown directory, aborting with 404 if missing."""
    d = Path(app.root_path) / "static" / "data" / "news"
    if not d.exists():
        abort(404, f"News folder not found: {d}")
    return d


def _iter_md_paths():
    """Yield all Markdown paths in the news directory, skipping the template file."""
    for p in sorted(_news_dir().glob("**/*.md")):
        if p.is_file() and p.stem.lower() != "news-template":
            yield p


def _load_md(path: Path):
    """
    Parse a Markdown file with YAML front matter.
    Returns (meta_dict, body_markdown_string).
    Raises ValueError if the front matter block is not found.
    """
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        raise ValueError(f"Front matter not found in {path.name}")
    meta = yaml.safe_load(m.group(1)) or {}
    body_markdown = m.group(2).strip()
    return meta, body_markdown


def _parse_date(meta: dict):
    """
    Parse the `date` field from front matter.
    Returns (date_obj, formatted_string).  date_obj is None if parsing fails.
    """
    date_obj = None
    if meta.get("date"):
        try:
            date_obj = dateparser.parse(str(meta["date"])).date()
        except Exception:
            pass
    date_str = date_obj.strftime("%d %b %Y").lstrip("0") if date_obj else ""
    return date_obj, date_str


def _make_teaser(meta: dict, body_md: str, limit: int = 240) -> str:
    """
    Return the post teaser.
    Uses the explicit `teaser` front matter field if present, otherwise
    takes the first paragraph of the Markdown body (truncated to `limit` chars).
    """
    teaser = (meta.get("teaser") or "").strip()
    if teaser:
        return teaser
    first_para = next((p.strip() for p in body_md.split("\n\n") if p.strip()), "")
    return (first_para[:limit] + "...") if len(first_para) > limit else first_para


def _reading_time(meta: dict, body_md: str) -> int:
    """
    Estimate reading time in minutes (200 wpm).
    Uses `reading_time` front matter field if present.
    """
    if meta.get("reading_time"):
        return int(meta["reading_time"])
    words = len(re.findall(r"\w+", body_md))
    return max(1, round(words / 200))


def _build_news_items(paths) -> list:
    """
    Build the list of news item dicts from a collection of Markdown paths.
    Skips files that fail to parse and logs the error.
    """
    items = []
    for path in paths:
        try:
            meta, body_md = _load_md(path)
            title = meta.get("title") or path.stem.replace("-", " ").title()
            date_obj, date_str = _parse_date(meta)
            hero = meta.get("hero") or {}
            items.append({
                "title":        title,
                "date":         date_obj,
                "date_str":     date_str,
                "author":       meta.get("author", ""),
                "teaser":       _make_teaser(meta, body_md),
                "reading_time": _reading_time(meta, body_md),
                "tags":         meta.get("tags") or [],
                "slug":         path.stem,
                "url":          url_for("news_post", slug=path.stem),
                "hero_src":     hero.get("src") or "",
                "hero_alt":     hero.get("alt", ""),
            })
        except Exception as exc:
            print(f"[news] Skipping {path.name}: {exc}")
    items.sort(key=lambda x: (x["date"] is not None, x["date"]), reverse=True)
    return items

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """
    Homepage: hero, about, work packages, news carousel, team, partners, contact.
    Passes the latest 9 news items (3 slides of 3) for the carousel.
    Team members are shuffled each request so no one is always first.
    """
    news_items = _build_news_items(_iter_md_paths())
    news_preview = news_items[:9]

    team_path = Path(app.root_path) / "static" / "data" / "team.json"
    try:
        members = json.loads(team_path.read_text(encoding="utf-8"))
        random.shuffle(members)
    except Exception as exc:
        print(f"[index] Could not load team.json: {exc}")
        members = []

    return render_template("index.html", news_preview=news_preview, members=members)


@app.route("/overview.html")
def overview():
    """About / Overview page with sticky TOC and work package sections."""
    return render_template("overview.html")


@app.route("/news.html")
def news():
    """
    News listing page with tag filters and client-side pagination.
    All news items are passed to the template; filtering and pagination
    happen in JavaScript so the frozen static site works without a server.
    """
    items = _build_news_items(_iter_md_paths())
    return render_template("news_list.html", news_items=items)


@app.route("/news/<slug>.html")
def news_post(slug):
    """
    Individual news post page.
    Renders the Markdown body to HTML, then applies postprocess_body in the
    template to fix image paths for both dev and frozen modes.
    """
    path = next((p for p in _iter_md_paths() if p.stem == slug), None)
    if path is None:
        abort(404)

    meta, body_md = _load_md(path)
    date_obj, date_str = _parse_date(meta)

    # Convert Markdown to HTML with useful extensions.
    # `smarty` converts straight quotes and ... to typographic equivalents.
    body_html = md.markdown(
        body_md,
        extensions=["fenced_code", "tables", "attr_list", "smarty", "toc"]
    )

    # Related posts: up to 2 most recent items that share at least one tag.
    post_tags = set(t.lower() for t in (meta.get("tags") or []))
    all_items = _build_news_items(_iter_md_paths())
    related = [
        it for it in all_items
        if it["slug"] != slug
        and bool(post_tags & {t.lower() for t in it["tags"]})
    ][:2]

    # Canonical URL for SEO.
    if meta.get("permalink"):
        canonical = meta["permalink"].strip()
    else:
        rel = url_for("news_post", slug=slug).lstrip("/")
        origin = (app.config.get("SITE_ORIGIN") or request.url_root).rstrip("/")
        canonical = f"{origin}/{rel}"

    return render_template(
        "news_post.html",
        slug=slug,
        body_html=body_html,
        date_str=date_str,
        date_obj=date_obj,
        canonical=canonical,
        related=related,
        **meta,
    )


if __name__ == "__main__":
    app.run(debug=True)
