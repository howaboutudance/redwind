from . import contexts
from . import util
from .models import Venue
from .views import geo_name

from bs4 import BeautifulSoup
from flask import request, jsonify, redirect, url_for, Blueprint, current_app, render_template
import datetime
import mf2py
import mf2util
import requests
import sys
import urllib

services = Blueprint('services', __name__)


@services.route('/api/mf2')
def old_convert_mf2():
    return redirect(url_for('.convert_mf2'))


@services.route('/services/mf2', methods=['GET', 'POST'])
def convert_mf2():
    strip_rel_urls = request.args.get('strip_rel_urls') or request.form.get('strip_rel_urls')
    url = request.args.get('url') or request.form.get('url')
    doc = request.args.get('doc') or request.form.get('doc')
    doc = doc and doc.strip()

    if url and not doc:
        parsed = urllib.parse.urlparse(url)
        if parsed.fragment:
            r = requests.get(url)
            r.raise_for_status()
            doc = BeautifulSoup(
                r.text if 'charset' in r.headers.get('content-type', '') 
                else r.content)
            doc = doc.find(id=parsed.fragment)

    if url or doc:
        try:
            json = mf2py.parse(url=url, doc=doc)
            if strip_rel_urls:
                json.pop('rel-urls', None)
            return jsonify(json)
        except:
            return jsonify({'error': str(sys.exc_info()[0])})

    return """
<html><body>
<h1>mf2py</h1>
<style>
body { max-width: 640px; margin: 0 auto; font-family: sans-serif; }
label { display: inline-block; font-weight: bold; }
input[type="text"],textarea { width: 100% }
</style>

<form method="get">
<label>URL to parse:</label>
<input type="text" name="url"/>
<input type="Submit">
</form>
<form method="post">
<div>
<label>Document to parse:</label>
<textarea name="doc" rows="10"></textarea>
</div>
<label>Base URL:</label>
<div>
<input type="text" name="url"/>
</div>
<div>
<label><input type="checkbox" name="strip_rel_urls"> Strip rel-urls</label>
</div>
<input type="Submit">
</form></body></html> """


@services.route('/api/mf2util')
def old_convert_mf2util():
    return redirect(url_for('.convert_mf2util'))


@services.route('/services/mf2util')
def convert_mf2util():
    def dates_to_string(json):
        if isinstance(json, dict):
            return {k: dates_to_string(v) for (k, v) in json.items()}
        if isinstance(json, list):
            return [dates_to_string(v) for v in json]
        if isinstance(json, datetime.date) or isinstance(json, datetime.datetime):
            return json.isoformat()
        return json

    url = request.args.get('url')
    as_feed = request.args.get('as-feed')
    if url:
        try:
            d = mf2py.parse(url=url)
            if as_feed == 'true' or mf2util.find_first_entry(d, ['h-feed']):
                json = mf2util.interpret_feed(d, url)
            else:
                json = mf2util.interpret(d, url)
            return jsonify(dates_to_string(json))
        except:
            return jsonify({'error': str(sys.exc_info()[0])})

    return """
<html><body>
<h1>mf2util</h1>
<form><p><label>URL to parse: <input name="url"></label>
<input type="Submit"/></p>
<p><label><input type="checkbox" value="true" name="as-feed"/>Parse as h-feed</label></p>
</form></body></html>"""


@services.route('/services/fetch_profile')
def fetch_profile():
    url = request.args.get('url')
    if not url:
        return """
<html><body>
<h1>Fetch Profile</h1>
<form><label>URL to fetch: <input name="url"></label>
<input type="Submit">
</form></body></html>"""

    from .util import TWITTER_PROFILE_RE, FACEBOOK_PROFILE_RE
    try:
        name = None
        twitter = None
        facebook = None
        image = None

        d = mf2py.Parser(url=url).to_dict()

        relmes = d['rels'].get('me', [])
        for alt in relmes:
            m = TWITTER_PROFILE_RE.match(alt)
            if m:
                twitter = m.group(1)
            else:
                m = FACEBOOK_PROFILE_RE.match(alt)
                if m:
                    facebook = m.group(1)

        # check for h-feed
        hfeed = next((item for item in d['items']
                      if 'h-feed' in item['type']), None)
        if hfeed:
            authors = hfeed.get('properties', {}).get('author')
            images = hfeed.get('properties', {}).get('photo')
            if authors:
                if isinstance(authors[0], dict):
                    name = authors[0].get('properties', {}).get('name')
                    image = authors[0].get('properties', {}).get('photo')
                else:
                    name = authors[0]
            if images and not image:
                image = images[0]

        # check for top-level h-card
        for item in d['items']:
            if 'h-card' in item.get('type', []):
                if not name:
                    name = item.get('properties', {}).get('name')
                if not image:
                    image = item.get('properties', {}).get('photo')

        return jsonify({
            'name': name,
            'image': image,
            'twitter': twitter,
            'facebook': facebook,
        })

    except BaseException as e:
        resp = jsonify({'error': str(e)})
        resp.status_code = 400
        return resp


@services.route('/services/nearby')
def nearby_venues():
    lat = float(request.args.get('latitude'))
    lng = float(request.args.get('longitude'))
    venues = Venue.query.all()

    venues.sort(key=lambda venue: (float(venue.location['latitude']) - lat) ** 2
                + (float(venue.location['longitude']) - lng) ** 2)

    return jsonify({
        'venues': [{
            'id': venue.id,
            'name': venue.name,
            'latitude': venue.location['latitude'],
            'longitude': venue.location['longitude'],
            'geocode': geo_name(venue.location),
        } for venue in venues[:10]]
    })


@services.route('/services/fetch_context')
def fetch_context_service():
    results = []
    for url in request.args.getlist('url[]'):
        ctx = contexts.create_context(url)
        results.append({
            'title': ctx.title,
            'permalink': ctx.permalink,
            'html': render_template(
                'admin/_context.jinja2', type=request.args.get('type'),
                context=ctx),
        })

    return jsonify({'contexts': results})


@services.route('/yt/<video>/<slug>/')
def youtube_shortener(video, slug):
    return redirect('https://youtube.com/watch?v={}'.format(video))


@services.route('/services/youtube/')
def create_youtube_link():
    url = request.args.get('url')
    if url:
        m = util.YOUTUBE_RE.match(url)
        if m:
            video_id = m.group(1)
            resp = requests.get(url)
            soup = BeautifulSoup(resp.text)
            title = soup.find('meta', {'property':'og:title'}).get('content')
            if title:
                url = url_for('.youtube_shortener', video=video_id, slug=util.slugify(title), _external=True)
                return """<a href="{}">{}</a>""".format(url, url)

    return """<form><input name="url"/><input type="submit"/></form>"""
