'''
The Pirate Bay Unofficial API - 2026 JSON-Powered Version
'''
import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

APP = Flask(__name__)
CORS(APP)

# The official internal API backend
API_URL = "https://apibay.org"

@APP.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "online",
        "endpoints": ["/search/<term>", "/recent", "/top/<cat>"]
    }), 200

@APP.route('/recent/', methods=['GET'])
@APP.route('/recent/<int:page>/', methods=['GET'])
def recent_torrents(page=1):
    # apibay uses previews.php for recent
    url = f"{API_URL}/previews.php?recent=1"
    return jsonify(fetch_api(url)), 200

@APP.route('/top/<int:cat>/', methods=['GET'])
def top_torrents(cat=0):
    # apibay uses top 100
    url = f"{API_URL}/previews.php?top={cat}"
    return jsonify(fetch_api(url)), 200

@APP.route('/search/<term>/', methods=['GET'])
@APP.route('/search/<term>/<int:page>/', methods=['GET'])
def search_torrents(term=None, page=1):
    # apibay uses q.php for search
    url = f"{API_URL}/q.php?q={term}&cat=0"
    return jsonify(fetch_api(url)), 200

def fetch_api(url):
    '''Hits the apibay JSON backend and formats it to match your expected schema'''
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://thepiratebay.org/'
    }
    
    try:
        print(f"Requesting API: {url}")
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        raw_data = res.json()
        
        # If apibay returns a list of dictionaries
        formatted_results = []
        for item in raw_data:
            # apibay returns 'id': '0' if no results found
            if item.get('id') == '0' or not item.get('info_hash'):
                continue
                
            formatted_results.append({
                'title': item.get('name'),
                'magnet': f"magnet:?xt=urn:btih:{item.get('info_hash')}&dn={item.get('name')}",
                'seeds': int(item.get('seeders', 0)),
                'leeches': int(item.get('leechers', 0)),
                'size': int(item.get('size', 0)),
                'uploader': item.get('username'),
                'category': item.get('category'),
                'id': item.get('id')
            })
        return formatted_results
        
    except Exception as e:
        print(f"API Error: {e}")
        return []

if __name__ == '__main__':
    APP.run(host='0.0.0.0', port=5000)
