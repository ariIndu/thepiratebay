'''
The Pirate Bay Unofficial API - Robust 2026 Version
'''
import os
import requests
import re
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

# Must match Dockerfile: app:APP
APP = Flask(__name__)
CORS(APP)
EMPTY_LIST = []

# Cleanup BASE_URL from env to prevent // errors
BASE_URL = os.getenv('BASE_URL', 'https://tpb.party').rstrip('/')

# Translation table for sorting filters
sort_filters = {
    'title_asc': 1, 'title_desc': 2, 'time_desc': 3, 'time_asc': 4,
    'size_desc': 5, 'size_asc': 6, 'seeds_desc': 7, 'seeds_asc': 8,
    'leeches_desc': 9, 'leeches_asc': 10, 'uploader_asc': 11,
    'uploader_desc': 12, 'category_asc': 13, 'category_desc': 14
}

def get_headers():
    '''Returns headers to bypass basic bot detection'''
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': f'{BASE_URL}/',
    }

@APP.route('/', methods=['GET'])
def index():
    return jsonify({"status": "online", "message": "TPB API is active"}), 200

@APP.route('/top/<int:cat>/', methods=['GET'])
def top_torrents(cat=0):
    sort = request.args.get('sort')
    sort_arg = sort if sort in sort_filters else ''
    cat_path = 'all' if cat == 0 else str(cat)
    url = f"{BASE_URL}/top/{cat_path}/{sort_arg}"
    return jsonify(parse_page(url, sort=sort)), 200

@APP.route('/recent/', methods=['GET'])
@APP.route('/recent/<int:page>/', methods=['GET'])
def recent_torrents(page=1):
    url = f"{BASE_URL}/recent/{page}"
    return jsonify(parse_page(url)), 200

@APP.route('/search/<term>/', methods=['GET'])
@APP.route('/search/<term>/<int:page>/', methods=['GET'])
def search_torrents(term=None, page=1):
    sort = request.args.get('sort')
    sort_val = sort_filters.get(sort, '')
    url = f"{BASE_URL}/search/{term}/{page}/{sort_val}"
    return jsonify(parse_page(url, sort=sort)), 200

def parse_page(url, sort=None):
    try:
        print(f"Scraping: {url}")
        res = requests.get(url, headers=get_headers(), timeout=15)
        res.raise_for_status()
        data = res.text
    except Exception as e:
        print(f"Scrape Failed: {e}")
        return EMPTY_LIST

    soup = BeautifulSoup(data, 'lxml')
    if not soup.find('table', {'id': 'searchResult'}):
        print("Table not found. Mirror might be blocking or changed HTML structure.")
        return EMPTY_LIST

    # Extract all components
    titles = [t.get_text() for t in soup.find_all(class_='detLink')]
    links = [l['href'] for l in soup.find_all('a', class_='detLink', href=True)]
    
    # Magnet links
    all_links = soup.find('table', {'id': 'searchResult'}).find_all('a', href=True)
    magnets = [m['href'] for m in all_links if 'magnet' in m['href']]

    # Seeders/Leechers
    slinfo = [s.get_text() for s in soup.find_all('td', {'align': 'right'})]
    seeders = slinfo[::2]
    leechers = slinfo[1::2]

    # Description (Robust version)
    times, sizes, uploaders = parse_description(soup)
    
    # Categories
    raw_cats = [c.get_text().replace('(', '').replace(')', '').split() for c in soup.find_all('center')]
    cat = [c[0] if c else "Other" for c in raw_cats]
    subcat = [" ".join(c[1:]) if len(c) > 1 else "Other" for c in raw_cats]

    torrents = []
    # Zip everything safely
    for i in range(len(titles)):
        try:
            torrents.append({
                'title': titles[i],
                'magnet': magnets[i] if i < len(magnets) else "",
                'time': convert_to_date(times[i]) if i < len(times) else "Unknown",
                'size': convert_to_bytes(sizes[i]) if i < len(sizes) else 0,
                'uploader': uploaders[i] if i < len(uploaders) else "Unknown",
                'seeds': int(seeders[i]) if i < len(seeders) else 0,
                'leeches': int(leechers[i]) if i < len(leechers) else 0,
                'category': cat[i] if i < len(cat) else "Unknown",
                'subcat': subcat[i] if i < len(subcat) else "Unknown",
                'id': links[i] if i < len(links) else "",
            })
        except: continue

    if sort and '_' in sort:
        try:
            field, direction = sort.split('_')
            torrents.sort(key=lambda x: x.get(field, 0), reverse=(direction.upper() == 'DESC'))
        except: pass

    return torrents

def parse_description(soup):
    desc_tags = soup.find_all('font', class_='detDesc')
    times, sizes, uploaders = [], [], []
    for d in desc_tags:
        text = d.get_text().replace(u'\xa0', u' ')
        parts = text.split(',')
        times.append(parts[0].replace('Uploaded ', '').strip() if len(parts) > 0 else "")
        sizes.append(parts[1].replace(' Size ', '').strip() if len(parts) > 1 else "")
        uploaders.append(parts[2].replace(' ULed by ', '').strip() if len(parts) > 2 else "Unknown")
    return times, sizes, uploaders

def convert_to_bytes(size_str):
    try:
        data = size_str.split()
        if len(data) < 2: return 0
        multipliers = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
        mag = float(data[0])
        exp = multipliers.index(data[1])
        return int(mag * (1024 ** exp))
    except: return 0

def convert_to_date(date_str):
    try:
        date_str = date_str.strip()
        if 'min' in date_str:
            mins = int(re.findall(r'\d+', date_str)[0])
            return (datetime.now() - timedelta(minutes=mins)).strftime('%Y-%m-%d %H:%M')
        if 'Today' in date_str:
            return date_str.replace('Today', datetime.now().strftime('%Y-%m-%d'))
        if 'Y-day' in date_str:
            yesterday = datetime.now() - timedelta(days=1)
            return date_str.replace('Y-day', yesterday.strftime('%Y-%m-%d'))
        return date_str
    except: return date_str

if __name__ == '__main__':
    APP.run(host='0.0.0.0', port=5000)
