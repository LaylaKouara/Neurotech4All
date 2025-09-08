# app/app.py
import os
import json
import random
<<<<<<< HEAD
from flask import Flask, render_template, request, abort, url_for
from pathlib import Path
import re, yaml
from dateutil import parser as dateparser
import markdown as md

=======
from flask import Flask, render_template, request, abort
from app.posts import *
=======
=======
>>>>>>> parent of da7984f (Added News Templates)
from flask import Flask, render_template, request, abort

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

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< Updated upstream
=======
=======
>>>>>>> parent of da7984f (Added News Templates)
=======
>>>>>>> parent of da7984f (Added News Templates)
@app.route('/news.html')
def news():
    news_path = os.path.join(app.root_path, 'static', 'data', 'news.json')
    with open(news_path) as f:
        news_items = json.load(f)
    return render_template('news.html', news_items=news_items)

<<<<<<< HEAD
<<<<<<< HEAD
>>>>>>> Stashed changes
=======

>>>>>>> parent of da7984f (Added News Templates)
=======

>>>>>>> parent of da7984f (Added News Templates)
@app.route('/contact.html')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
