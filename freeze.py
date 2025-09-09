from pathlib import Path
from app.app import app
from flask_frozen import Freezer

base_dir = Path(__file__).resolve().parent          # repo root (where freeze.py lives)
output_dir = base_dir / "docs"                      # repo-level docs/

app.config['FREEZER_MODE'] = True  # Enable frozen mode when freezing
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['FREEZER_DESTINATION'] = str(output_dir)

#  public URL
app.config['SITE_ORIGIN'] = "https://neurotech4all.com"

freezer = Freezer(app)

@freezer.register_generator
def page_routes():
    yield '/'
    yield '/overview.html'
    yield '/team.html'
    yield '/resources.html'
    yield '/news_contents.html'
    yield '/contact.html'

# freeze.py  (add this under your existing generators)

@freezer.register_generator
def news_post_routes():
    """
    Generate /news/<slug>.html for every Markdown file under static/data/news.
    """
    news_dir = Path(app.root_path) / "static" / "data" / "news"
    for path in sorted(news_dir.glob("**/*.md")):
        if not path.is_file():
            continue
        if path.stem.lower() == "news-template":
            continue
        yield 'news_post', {'slug': path.stem}


if __name__ == '__main__':
    freezer.freeze()
