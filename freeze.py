from pathlib import Path
from app.app import app
from flask_frozen import Freezer

base_dir = Path(__file__).resolve().parent          # repo root (where freeze.py lives)
output_dir = base_dir / "docs"                      # repo-level docs/

app.config['FREEZER_MODE'] = True  # Enable frozen mode when freezing
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['FREEZER_DESTINATION'] = str(output_dir)


freezer = Freezer(app)

@freezer.register_generator
def page_routes():
    yield '/'
    yield '/overview.html'
    yield '/team.html'
    yield '/resources.html'
    yield '/news.html'
    yield '/contact.html'

if __name__ == '__main__':
    freezer.freeze()
