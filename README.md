# Neurotech4All Website

The site is built with Flask and published as static HTML to GitHub Pages at [www.neurotech4all.com](https://www.neurotech4all.com).

---

## What to edit

### News posts

Add a new Markdown file to `app/static/data/news/`. Copy `news-template.md` as a starting point. The filename becomes the URL (e.g. `my-post.md` becomes `/news/my-post.html`).

Each file starts with a block of metadata at the top (YAML front matter), then the article body in Markdown. Example:

```
---
title: "Your Post Title"
date: "15 Jan 2026"
author: "Your Name"
teaser: "One sentence shown on the news listing page."
reading_time: 3
tags: [Parkinson's, Conference]

hero:
  src: "data/news/images/your-image.jpg"
  alt: "Description of image"
  caption: "Optional caption shown under the image."
---

Your article content goes here, written in Markdown.
```

Put images for the post in `app/static/data/news/images/`. Use lowercase filenames with hyphens (e.g. `my-event-photo.jpg`).

> Do not use the `news-template.md` filename for a real post. It is skipped during the build.

---

### Team members

Edit `app/static/data/team.json`. Each person is one object in the list:

```json
{
  "name": "Full Name",
  "role": "Job Title",
  "image": "images/firstname-lastname.jpg",
  "linkedin": "https://www.linkedin.com/in/...",
  "bio": "One or two sentences about this person."
}
```

Put the photo in `app/static/images/`. Use lowercase filenames with hyphens.

---

### Navigation, footer, and partners

Edit `app/static/data/site_config.json`. This file controls:

- `nav.links` - the navigation bar items and order
- `footer.columns` - the footer link columns
- `partners` - the partner logos shown on the homepage
- `site` - the site name, email address, social links, and contact form ID

Partner logos can be external URLs (`"logo": "https://..."`) or local files (`"logo_local": "images/filename.png"`). Local files go in `app/static/images/`.

---

## What NOT to edit

| Path | Reason |
|---|---|
| `app/templates/` | HTML templates. Changes here affect every page. |
| `app/app.py` | The Flask application. Do not touch unless you know Python/Flask. |
| `app/static/css/main.css` | All site styles. Do not touch unless you know CSS. |
| `freeze.py` | The build script that generates the static site. |
| `docs/` | Auto-generated output. Never edit these files directly. They are overwritten every time you build. |

---

## Making changes live

### 1. Set up (first time only)

Install the required Python packages:

```
pip install -r requirements.txt
```

### 2. Preview your changes

Run the development server:

```
python app/app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. The server reloads automatically when you edit templates or Python files. For changes to `site_config.json` or `team.json`, restart the server (Ctrl+C, then run again).

### 3. Build the static site

When you are happy with the changes, generate the static files:

```
python freeze.py
```

This writes everything to `docs/`.

### 4. Publish

Commit and push to GitHub. GitHub Pages serves the site automatically from the `docs/` folder.
