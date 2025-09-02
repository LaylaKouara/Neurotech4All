# app/content/posts.py
from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict

import yaml
import markdown

# Where editors drop .md files (with YAML front matter)
POSTS_DIR = Path(__file__).resolve().parents[1] / "data" / "posts"

# Simple in-process cache
_POSTS_CACHE: Optional[List[Dict]] = None


def _parse_md_with_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            fm, body = parts[1], parts[2]
            meta = yaml.safe_load(fm) or {}
            return meta, body.lstrip()
    return {}, text


def _parse_date(dval) -> Optional[datetime]:
    if isinstance(dval, datetime):
        return dval
    if isinstance(dval, (int, float)):
        return datetime.fromtimestamp(dval)
    if isinstance(dval, str):
        # Try ISO first, then a few common UK-ish formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(dval, fmt)
            except ValueError:
                continue
    return None


def _date_display(dt: Optional[datetime]) -> str:
    return dt.strftime("%d %b %Y") if dt else ""


def _author_initials(name: str, override: Optional[str] = None) -> str:
    if override:
        return override.upper()
    if not name:
        return "NA"
    parts = re.findall(r"[A-Za-z]+", name)
    if not parts:
        return "NA"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _reading_time(text: str, wpm: int = 200) -> int:
    words = re.findall(r"\w+", text)
    return max(1, round(len(words) / wpm))


def _slug_from(meta: dict) -> str:
    dt = _parse_date(meta.get("date")) or datetime.today()
    initials = _author_initials(meta.get("author", ""), meta.get("author_initials"))
    return f"{dt.strftime('%d-%m-%Y')}-{initials}"


def _ensure_posts_dir():
    POSTS_DIR.mkdir(parents=True, exist_ok=True)


def _build_post(md_path: Path) -> Dict:
    raw = md_path.read_text(encoding="utf-8")
    meta, body_md = _parse_md_with_frontmatter(raw)

    dt = _parse_date(meta.get("date"))
    post = {
        **meta,
        "date_obj": dt,
        "date_display": meta.get("date_display") or _date_display(dt),
        "reading_time": meta.get("reading_time") or _reading_time(body_md),
        "slug": _slug_from(meta),
        "_body_md": body_md,
    }
    post["url"] = f"/news/{post['slug']}/"
    return post


def load_posts(force: bool = False) -> List[Dict]:
    """Load and cache posts sorted by date desc."""
    global _POSTS_CACHE
    if _POSTS_CACHE is not None and not force:
        return _POSTS_CACHE

    _ensure_posts_dir()
    posts = []
    for md in POSTS_DIR.glob("*.md"):
        try:
            posts.append(_build_post(md))
        except Exception:
            # Skip bad files; in production you might log this
            continue

    posts.sort(key=lambda p: (p.get("date_obj") or datetime.min), reverse=True)
    _POSTS_CACHE = posts
    return posts


def news_index_items(force: bool = False) -> List[Dict]:
    """Return lightweight items for the news listing page."""
    items = []
    for p in load_posts(force=force):
        items.append({
            "title": p.get("title", p["slug"]),
            "summary": p.get("teaser", ""),
            "date_display": p.get("date_display", ""),
            "url": p["url"],
            "tags": p.get("tags", []),
            "author": p.get("author", ""),
            "author_initials": _author_initials(p.get("author", ""), p.get("author_initials")),
        })
    return items


def get_post_page(slug: str, force: bool = False) -> Optional[Tuple[Dict, str, Optional[Dict], Optional[Dict]]]:
    """Return (post, content_html, prev_ctx, next_ctx) for a slug."""
    posts = load_posts(force=force)
    if not posts:
        return None
    by_slug = {p["slug"]: p for p in posts}
    p = by_slug.get(slug)
    if not p:
        return None

    idx = posts.index(p)
    prev = posts[idx - 1] if idx - 1 >= 0 else None
    nxt = posts[idx + 1] if idx + 1 < len(posts) else None
    prev_ctx = {"title": prev.get("title", prev["slug"]), "url": prev["url"]} if prev else None
    next_ctx = {"title": nxt.get("title", nxt["slug"]), "url": nxt["url"]} if nxt else None

    content_html = markdown.markdown(
        p["_body_md"],
        extensions=['extra', 'sane_lists', 'toc', 'attr_list']
    )

    post_ctx = dict(p)  # shallow copy; templates can rely on 'post'
    return post_ctx, content_html, prev_ctx, next_ctx


# Helper for freeze.py (optional):
def iter_urls() -> List[str]:
    """All news URLs for freezing."""
    return [p["url"] for p in load_posts()]
