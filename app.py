'''
The Pirate Bay Unofficial API - 2026 Production Version
Uses Cloudscraper to bypass Cloudflare and the Apibay JSON backend for reliability.
'''
import os
import cloudscraper
from flask import Flask, jsonify, request
from flask_cors import CORS

# Must match Dockerfile: app:APP
APP = Flask(__name__)
CORS(APP)

# Initialize the bypass scraper
# This mimics a real browser to get past Cloudflare "Checking your browser" screens
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

API_URL = "https://apibay.org"

@APP.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "online",
        "provider": "apibay-json",
        "bypass_engine": "cloudscraper",
        "endpoints": {
            "search": "/search/<term>/<page>",
            "recent": "/recent",
            "top": "/top/<category_code>"
        }
    }), 200

@APP.route('/recent/', methods=['GET'])
@APP.route('/recent/<int:page>/', methods=['GET'])
def recent_torrents(page=1):
    # Apibay recent endpoint
    url = f"{API_URL}/previews.php?recent=1"
    return jsonify(fetch_and_format(url)), 200

@APP.route('/top/<int:cat>/', methods=['GET'])
def top_torrents(cat=0):
    # Apibay top 100 endpoint
    url = f"{API_URL}/previews.php?top={cat}"
    return jsonify(fetch_and_format(url)), 200

@APP.route('/search/<term>/', methods=['GET'])
@APP.route('/search/<term>/<int:page>/', methods=['GET'])
def search_torrents(term=None, page=1):
    # Apibay search endpoint
    # Note: Apibay handles pagination differently, but term/cat are the basics
    url = f"{API_URL}/q.php?q={term}&cat=0"
    return jsonify(fetch_and_format(url)), 200

def fetch_and_format(url):
    '''Hits the backend using cloudscraper and formats the result'''
    try:
        print(f"Bypassing Cloudflare for: {url}")
        response = scraper.get(url, timeout=15)
        
        # If the mirror is down or blocking Render's IP entirely
        if response.status_code != 200:
            print(f"Error: Backend returned status {response.status_code}")
            return []

        raw_data = response.json()
        
        # Check for empty results (Apibay returns [{'id': '0', ...}] for no results)
        if not raw_data or (isinstance(raw_data, list) and raw_data[0].get('id') == '0'):
            return []

        formatted_results = []
        for item in raw_data:
            # Constructing a standard dictionary similar to your original code
            formatted_results.append({
                'title': item.get('name'),
                'magnet': f"magnet:?xt=urn:btih:{item.get('info_hash')}&dn={item.get('name')}",
                'seeds': int(item.get('seeders', 0)),
                'leeches': int(item.get('leechers', 0)),
                'size': int(item.get('size', 0)),  # Size is already in bytes from this API
                'uploader': item.get('username', 'Anonymous'),
                'category': item.get('category', '0'),
                'id': item.get('id', '0'),
                'added': item.get('added', '0') # Timestamp
            })
        
        # Optional: Handle the sorting if the user passed the ?sort=seeds_desc param
        sort = request.args.get('sort')
        if sort and '_' in sort:
            field, direction = sort.split('_')
            # Mapping seeds_desc to the internal key 'seeds'
            key_map = {'seeds': 'seeds', 'leeches': 'leeches', 'size': 'size', 'title': 'title'}
            field_key = key_map.get(field)
            if field_key:
                formatted_results.sort(
                    key=lambda x: x.get(field_key, 0) if field_key != 'title' else x.get(field_key, '').lower(),
                    reverse=(direction.upper() == 'DESC')
                )

        return formatted_results

    except Exception as e:
        print(f"Critical API Error: {e}")
        return []

if __name__ == '__main__':
    # For local testing
    APP.run(host='0.0.0.0', port=5000)
