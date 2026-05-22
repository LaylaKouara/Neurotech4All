# freeze.py
#
# Builds static HTML into docs/ for GitHub Pages deployment.
# Run with:  python freeze.py
#
# Flask-Frozen crawls all registered routes and writes each to a file.
# The CNAME file is written at the end so GitHub Pages uses the custom domain.

from pathlib import Path
from app.app import app
from flask_frozen import Freezer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

base_dir   = Path(__file__).resolve().parent  # repo root
output_dir = base_dir / "docs"               # GitHub Pages source folder

app.config["FREEZER_MODE"]         = True          # switches asset/link helpers to relative URLs
app.config["FREEZER_RELATIVE_URLS"] = True
app.config["FREEZER_DESTINATION"]   = str(output_dir)
app.config["SITE_ORIGIN"]           = "https://www.neurotech4all.com"

freezer = Freezer(app)

# ---------------------------------------------------------------------------
# Route generators
# ---------------------------------------------------------------------------

@freezer.register_generator
def page_routes():
    """Register all top-level static pages."""
    yield "/"
    yield "/overview.html"
    yield "/news.html"


@freezer.register_generator
def news_post_routes():
    """
    Generate one URL per news Markdown file.
    Flask-Frozen cannot discover dynamic routes automatically, so we list them here.
    """
    news_dir = Path(app.root_path) / "static" / "data" / "news"
    for path in sorted(news_dir.glob("**/*.md")):
        if path.is_file() and path.stem.lower() != "news-template":
            yield "news_post", {"slug": path.stem}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_cname(domain: str = "www.neurotech4all.com") -> None:
    """Write the CNAME file that GitHub Pages needs for the custom domain."""
    dest = Path(app.config["FREEZER_DESTINATION"])
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "CNAME").write_text(domain + "\n", encoding="utf-8")
    print(f"Wrote CNAME -> {dest / 'CNAME'}")


if __name__ == "__main__":
    freezer.freeze()
    write_cname()
    print(f"Frozen to {output_dir}")
